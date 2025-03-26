from collections import OrderedDict
from time import sleep

from blackjack.analytics.metric_tracker import MetricTracker
from blackjack.exc import InsufficientBankrollError
from blackjack.models.card import Card
from blackjack.models.hand import DealerHand, GamblerHand
from blackjack.display_utils import clear, header, money_format, pct_format
import keyboard
import random


def render_after(instance_method):
    """Decorator for calling the `render()` instance method after calling an instance method."""

    def wrapper(self, *args, **kwargs):
        instance_method(self, *args, **kwargs)
        if self.verbose:
            self.render()

    return wrapper


def get_card_input(prompt):
    """Prompt the user to enter a card rank."""
    while True:
        card_input = input(prompt).strip()
        if not card_input:
            print("Input cannot be empty. Please enter a valid rank.")
            continue
        try:
            value = next(value for rank_name, value in Card.RANKS if rank_name == card_input)
            if isinstance(value, list):
                value = value[1]  # Use the higher value for Aces
            suit = random.choice(Card.SUITS)
            return Card(suit, card_input, value)
        except StopIteration:
            print("Invalid card rank. Please enter a valid rank.")


def get_total_input(prompt):
    """Prompt the user to enter a card total."""
    while True:
        try:
            total = int(input(prompt).strip())
            if total < 4 or total > 21:  # Minimum valid total is 4 (2+2), maximum is 21
                print("Invalid total. Please enter a value between 4 and 21.")
                continue
            return total
        except ValueError:
            print("Invalid input. Please enter a numeric value.")


def create_dummy_hand(total):
    """Create a hand with a dummy card that represents the total."""
    dummy_card = Card("Spades", f"Total:{total}", total)
    return [dummy_card]


class GameController:

    def __init__(self, gambler, dealer, shoe, strategy, verbose=True, max_turns=None):
        # Configured models from game setup
        self.gambler = gambler
        self.dealer = dealer
        self.shoe = shoe

        # Strategy to employ for in-game decision making
        self.strategy = strategy

        # Turn activity log
        self.activity = []

        # Render options
        self.verbose = verbose  # Switch for printing/suppressing output
        self.hide_dealer = True  # Switch for showing/hiding the dealer's buried card during rendering
        self.dealer_playing = False  # Switch for when dealer is playing and no user actions available

        # Keep track of number of turns played (and the max number of turns to play if applicable)
        self.turn = 0
        self.max_turns = max_turns

        # Metric tracking (for analytics)
        self.metric_tracker = MetricTracker()

    def play(self):
        """Main game loop that controls entire game flow."""
        # Track the starting bankroll
        self.metric_tracker.append_bankroll(self.gambler.bankroll)

        # Pause exectution until the user wants to proceed if applicable.
        if self.verbose:
            input('Press DEAL to proceed => ')

        # Play the game to completion
        while self.play_condition():

            # Increment the turn counter
            self.turn += 1

            # Initialize the activity log for the turn
            self.add_activity(f"Turn #{self.turn}")

            # Check for status text immediately after DEAL/REBET
            status_text = self.check_for_status_text()
            if status_text:
                self.handle_immediate_status(status_text)
                self.finalize_turn()
                continue

            # Vet the gambler's auto-wager against their bankroll, and ask if they would like to change their wager or cash out.
            self.check_gambler_wager()
            if self.gambler.auto_wager == 0:  # If they cashed out, don't play the turn. The game is over.
                break

            # Deal cards based on totals instead of individual cards
            self.deal()

            # Check for status text after dealing
            status_text = self.check_for_status_text()
            if status_text:
                self.handle_immediate_status(status_text)
                self.finalize_turn()
                continue

            # Carry out pre-turn flow (for blackjacks, insurance, etc).
            self.play_pre_turn()

            # Check for status text after pre-turn
            status_text = self.check_for_status_text()
            if status_text:
                self.handle_immediate_status(status_text)
                self.finalize_turn()
                continue

            # Play the gambler's turn (if necessary).
            self.play_gambler_turn()

            # Check for status text after gambler's turn
            status_text = self.check_for_status_text()
            if status_text:
                self.handle_immediate_status(status_text)
                self.finalize_turn()
                continue

            # Play the dealer's turn (if necessary).
            self.play_dealer_turn()

            # Settle gambler hand wins and losses.
            self.settle_up()

            # Track metrics and reset in order to proceed with the next turn.
            self.finalize_turn()

        # Render a game over message
        self.finalize_game()

    def play_condition(self):
        """Return True to play another turn, False otherwise."""
        # If the gambler is cashed out or out of money there is no turn to play.
        if self.gambler.is_finished():
            return False

        # If max number of turns imposed make sure we haven't hit it yet.
        if self.max_turns:
            return self.turn < self.max_turns

        # Checks have passed, play the turn.
        return True

    @render_after
    def add_activity(self, *messages):
        """Add message(s) to the activity log."""
        # Add all messages
        for message in messages:
            self.activity.append(message)

    def check_gambler_wager(self):
        """
        Pre-turn vetting of the gambler's wager.
        1. Check whether the gambler has enough bankroll to place their auto-wager. If not, set to remaining bankroll.
        2. Ask the gambler if they'd like to change their auto-wager or cash out. Allow them to do so.
        """
        # If the gambler doesn't have sufficient bankroll to place their auto-wager, set their auto-wager to their remaining bankroll.
        if not self.gambler.can_place_auto_wager():
            self.gambler.set_new_auto_wager(self.gambler.bankroll)
            self.add_activity(
                f"Insufficient bankroll to place current auto-wager. Setting auto-wager to remaining bankroll.")

        # Check whether the user wants to change their auto-wager or cash out.
        if self.strategy.wants_to_change_wager():
            self.set_new_auto_wager()

    def set_new_auto_wager(self):
        """Set a new auto-wager amount."""
        # Set the gambler's auto_wager to $0.00.
        self.gambler.zero_auto_wager()

        # Ask the gambler for a new auto wager and set it, with some validation.
        success = False
        while not success:
            # Get the new auto-wager from the strategy
            new_auto_wager = self.strategy.get_new_auto_wager()

            # This validates that they've entered a wager <= their bankroll
            try:
                self.gambler.set_new_auto_wager(new_auto_wager)
                success = True
            except InsufficientBankrollError as err:
                print(f"{err}. Please try again.")

    def deal(self):
        """Deal cards based on totals for both gambler and dealer."""


        # Get the dealer's upcard value
        dealer_upcard = get_card_input("Enter the dealer's upcard:")

        # Get the gambler's initial total
        gambler_total = get_total_input("Enter the gambler's initial total: ")

        # Create a dummy hand for the gambler with a card that represents the total
        gambler_cards = create_dummy_hand(gambler_total)

        # Create hands with the initial cards/totals
        self.gambler.hands.append(GamblerHand(cards=gambler_cards))
        self.dealer.hand = DealerHand(cards=[dealer_upcard])  # Only the upcard initially

        # Place the gambler's auto-wager on the hand
        self.gambler.place_auto_wager()

        # Log it
        self.add_activity('Dealing hands.')

        # Ensure dealer's cards are displayed appropriately
        self.hide_dealer = True

    def play_pre_turn(self):
        """Carry out pre-turn flow for blackjacks and insurance."""
        # --- BLACKJACK CHECKING FOR PRE-TURN FLOW --- #

        # Grab the gambler's dealt hand for pre-turn processing.
        gambler_hand = self.gambler.first_hand()

        # Check if the gambler has blackjack. Log it if so.
        gambler_has_blackjack = gambler_hand.final_total() == 21
        if gambler_has_blackjack:
            self.add_activity(f"{self.gambler.name} has blackjack.")

        # Check if the dealer has blackjack, but don't display it to the gambler yet.
        dealer_has_blackjack = self.dealer.hand.is_blackjack()

        # --- DEALER ACE PRE-TURN FLOW --- #

        # Insurance comes into play if the dealer's upcard is an ace
        if self.dealer.is_showing_ace():

            # Log it.
            self.add_activity('Dealer is showing an Ace.')

            # If the gambler has blackjack, they can either take even money or let it ride.
            if gambler_has_blackjack:

                if self.strategy.wants_even_money():
                    # Pay out even money (meaning 1:1 hand wager).
                    self.set_hand_outcome(gambler_hand, 'Even Money')
                    self.add_activity(f"{self.gambler.name} took even money.")
                else:
                    if dealer_has_blackjack:
                        # Both players have blackjack. Gambler reclaims their wager and that's all.
                        self.set_hand_outcome(gambler_hand, 'Push')
                        self.add_activity('Dealer has blackjack.', 'Hand is a push.')
                    else:
                        # Dealer does not have blackjack. Gambler has won a blackjack (which pays 3:2)
                        self.set_hand_outcome(gambler_hand, 'Win')
                        self.add_activity('Dealer does not have blackjack.', f"{self.gambler.name} wins 3:2.")

            # If the gambler does not have blackjack they can buy insurance.
            else:
                # Gambler must have sufficient bankroll to place an insurance bet.
                gambler_can_afford_insurance = self.gambler.can_place_insurance_wager()

                if gambler_can_afford_insurance and self.strategy.wants_insurance():

                    # Insurnace is a side bet that is half their wager, and pays 2:1 if dealer has blackjack.
                    self.gambler.place_insurance_wager()

                    # The turn is over if the dealer has blackjack. Otherwise, continue on to playing the hand.
                    if dealer_has_blackjack:
                        self.hide_dealer = False  # Show the dealer's blackjack.
                        self.set_hand_outcome(gambler_hand, 'Insurance Win')
                        self.add_activity('Dealer has blackjack.',
                                          f"{self.gambler.name}'s insurnace wager wins 2:1 (hand wager loses).")
                    else:
                        gambler_hand.lost_insurance = True
                        self.add_activity('Dealer does not have blackjack.',
                                          f"{self.gambler.name}'s insurance wager loses.")

                # If the gambler does not (or cannot) place an insurance bet, they lose if the dealer has blackjack. Otherwise, hand continues.
                else:
                    # Message for players who were not offered the option to place an insurance bet to due insufficient bankroll.
                    if not gambler_can_afford_insurance:
                        self.add_activity('Insufficient bankroll to place insurance wager.')

                    # The turn is over if the dealer has blackjack. Otherwise, continue on to playing the hand.
                    if dealer_has_blackjack:
                        self.hide_dealer = False
                        self.add_activity('Dealer has blackjack.', f"{self.gambler.name} loses the hand.")
                        self.set_hand_outcome(gambler_hand, 'Loss')
                    else:
                        self.add_activity('Dealer does not have blackjack.')

        # --- DEALER FACE CARD PRE-TURN FLOW --- #

        # If the dealer's upcard is a face card, insurance is not in play but need to check if the dealer has blackjack.
        elif self.dealer.is_showing_face_card():

            # Log the blackjack check.
            self.add_activity('Checking if the dealer has blackjack.')

            # If the dealer has blackjack, it's a push if the player also has blackjack. Otherwise, the player loses.
            if dealer_has_blackjack:

                self.hide_dealer = False
                self.add_activity('Dealer has blackjack.')

                if gambler_has_blackjack:
                    self.add_activity('Hand is a push.')
                    self.set_hand_outcome(gambler_hand, 'Push')
                else:
                    self.add_activity(f"{self.gambler.name} loses the hand.")
                    self.set_hand_outcome(gambler_hand, 'Loss')

            # If dealer doesn't have blackjack, the player wins if they have blackjack. Otherwise, play the turn.
            else:
                self.add_activity('Dealer does not have blackjack.')

                if gambler_has_blackjack:
                    self.add_activity(f"{self.gambler.name} wins 3:2.")
                    self.set_hand_outcome(gambler_hand, 'Win')

        # --- REGULAR PRE-TURN FLOW --- #

        # If the dealer's upcard is not an ace or a face card, they cannot have blackjack.
        # If the player has blackjack here, payout 3:2 and the hand is over. Otherwise, continue with playing the hand.
        else:
            if gambler_has_blackjack:
                self.add_activity(f"{self.gambler.name} wins 3:2.")
                self.set_hand_outcome(gambler_hand, 'Win')

    def play_gambler_turn(self):
        """Play the gambler's turn, meaning play all of the gambler's hands to completion."""
        # Keep dealer's second card hidden during gambler's turn
        self.hide_dealer = True

        # Log a message that the turn is being played, or there's no need to play it.
        if any(hand.status == 'Pending' for hand in self.gambler.hands):
            message = f"Playing {self.gambler.name}'s turn."
        else:
            message = f"No turn to play for {self.gambler.name}."
        self.add_activity(message)

        # Use a while loop due to the fact that self.hands can grow while iterating (via splitting)
        while any(hand.status == 'Pending' for hand in self.gambler.hands):
            hand = next(hand for hand in self.gambler.hands if hand.status == 'Pending')  # Grab the next unplayed hand
            self.play_gambler_hand(hand)

    def play_gambler_hand(self, hand):
        """Play a gambler hand."""
        self.set_hand_status(hand, 'Playing')

        while hand.status == 'Playing':
            # Handle special cases with only one card
            if len(hand.cards) == 1:
                current_total = hand.final_total()

                # If total is 21, it's a blackjack
                if current_total == 21:
                    self.set_hand_status(hand, 'Blackjack')
                    self.set_hand_outcome(hand, 'Win')
                    break

            # Check for status text after each player action
            status_text = self.check_for_status_text()
            if status_text:
                self.handle_immediate_status(status_text)
                return

            # Get available options and action from strategy
            options = self.get_hand_options(hand)
            action = self.strategy.get_hand_action(hand, options, self.dealer.up_card())
            input(f"Press ENTER to {action}...")

            if action == 'Hit':
                self.hit_hand(hand)
            elif action == 'Stand':
                self.set_hand_status(hand, 'Stood')
            elif action == 'Double':
                self.double_hand(hand)
            elif action == 'Split':
                self.split_hand(hand)
            elif action == 'Surrender':
                self.handle_surrender(hand)
            else:
                raise Exception('Unhandled response.')

            # Check hand status after action
            current_total = hand.final_total()
            if current_total == 21:
                self.set_hand_status(hand, 'Stood')
            elif current_total > 21:
                self.set_hand_status(hand, 'Busted')
                self.set_hand_outcome(hand, 'Loss')

    def handle_surrender(self, hand):
        """Handle the surrender action."""
        self.gambler.bankroll -= hand.wager / 2
        self.set_hand_status(hand, 'Surrendered')
        self.set_hand_outcome(hand, 'Surrender')
        self.add_activity(f"{self.gambler.name} has surrendered. Half of the bet is lost.")

    def get_hand_options(self, hand):
        """Get the options (available actions) that can be taken on a hand."""
        # Default options that are always available
        options = OrderedDict([('h', 'Hit'), ('s', 'Stand')])

        # Add the option to double if applicable
        if len(hand.cards) == 1 and self.gambler.can_place_wager(hand.wager):  # Only first action can be double
            options['d'] = 'Double'

        # Add the option to split if applicable - not applicable in our simplified version
        # but keeping the option structure consistent with the original

        return options

    @render_after
    def hit_hand(self, hand):
        """Update the hand total after hitting."""
        # Get the new total
        new_total = get_total_input("Enter the new total after hit: ")

        # Replace the dummy card with a new one representing the new total
        hand.cards = create_dummy_hand(new_total)

    def split_hand(self, hand):
        """Split hand - simplified for our total-based approach."""
        # This would require more complex implementation to track split hands
        # For now, just showing a message that split is not supported in this version
        self.add_activity("Split is not supported in the total-based version.")

    def double_hand(self, hand):
        """Double a hand, doubling the wager and getting a new total."""
        # Double the wager
        self.gambler.place_hand_wager(hand.wager, hand)

        # Get the new total after doubling
        new_total = get_total_input("Enter the new total after doubling: ")

        # Update the hand with the new total
        hand.cards = create_dummy_hand(new_total)

        # Set the status to Doubled
        self.set_hand_status(hand, 'Doubled')

    @render_after
    def set_hand_status(self, hand, status):
        """Set a new status for a hand."""
        hand.status = status

    @render_after
    def set_hand_outcome(self, hand, outcome):
        """Set the outcome of the hand, and change the status if applicable."""
        hand.outcome = outcome
        if hand.status == 'Pending':
            hand.status = 'Played'

    def play_dealer_turn(self):
        """Play the dealer's turn - simplified to just enter the dealer's final total."""
        # Only proceed if there are hands that need to be evaluated against the dealer
        if not any(hand.status in ('Doubled', 'Stood') for hand in self.gambler.hands):
            self.dealer_playing = False
            return

        self.add_activity("Entering the Dealer's final result.")
        hand = self.dealer.hand

        # Clear any existing cards after the first one
        upcard = hand.cards[0]
        hand.cards = [upcard]

        # Ask for dealer's final total
        while True:
            try:
                dealer_total = int(input("Enter the dealer's final total: "))
                if dealer_total < upcard.value:
                    print(f"Error: Total must be at least {upcard.value} (dealer's upcard value)")
                    continue
                break
            except ValueError:
                print("Please enter a valid number")

        # Create a dummy second card to represent the remaining points
        remaining_points = dealer_total - upcard.value
        dummy_card = Card("Hidden", "Total", remaining_points)
        hand.cards.append(dummy_card)

        # Set appropriate final status
        if dealer_total > 21:
            self.set_hand_status(hand, 'Busted')
            self.add_activity(f"Dealer busts with total of {dealer_total}")
        else:
            self.set_hand_status(hand, 'Stood')
            self.add_activity(f"Dealer stands with total of {dealer_total}")

        # Now reveal all dealer cards
        self.hide_dealer = False
        self.dealer_playing = False

    def pay_out_hand(self, hand, payout_type):
        """Pay out hand winnings, including wager reclaim."""
        # Pay out winning hand wagers 1:1 and reclaim the wager
        if payout_type == 'wager':
            self.perform_hand_payout(hand, 'winning_wager', '1:1')
            self.perform_hand_payout(hand, 'wager_reclaim')

        # Pay out winning blackjack hands 3:2 and reclaim the wager
        elif payout_type == 'blackjack':
            self.perform_hand_payout(hand, 'winning_wager', '3:2')
            self.perform_hand_payout(hand, 'wager_reclaim')

        # Pay out winning insurance wagers 2:1 and reclaim the insurance wager
        elif payout_type == 'insurance':
            self.perform_hand_payout(hand, 'winning_insurance', '2:1')
            self.perform_hand_payout(hand, 'insurance_reclaim')

        # Reclaim wager in case of a push
        elif payout_type == 'push':
            self.perform_hand_payout(hand, 'wager_reclaim')

        # Should not get here
        else:
            raise ValueError(f"Invalid payout type: '{payout_type}'")

    def perform_hand_payout(self, hand, payout_type, odds=None):
        """Determine hand winnings and execute the payout."""
        # Validate args passed in
        if payout_type in ('winning_wager', 'winning_insurance'):
            assert odds, 'Must specify odds for wager and insurance payouts!'
            antecedent, consequent = map(int, odds.split(':'))

        # Determine the payout amount by the payout_type (and odds if applicable)
        if payout_type == 'winning_wager':
            amount = hand.wager * antecedent / consequent
            message = f"Adding winning hand payout of {money_format(amount)} to bankroll."

        elif payout_type == 'wager_reclaim':
            amount = hand.wager
            message = f"Reclaiming hand wager of {money_format(amount)}."

        elif payout_type == 'winning_insurance':
            amount = hand.insurance * antecedent / consequent
            message = f"Adding winning insurance payout of {money_format(amount)} to bankroll."

        elif payout_type == 'insurance_reclaim':
            amount = hand.insurance
            message = f"Reclaiming insurance wager of {money_format(amount)}."

        else:
            raise ValueError(f"Invalid payout type: '{payout_type}'")

        hand.earnings += amount
        self.gambler.payout(amount)
        self.add_activity(f"Hand {hand.hand_number}: {message}")

    def determine_hand_outcome(self, hand, dealer_hand):
        """Determine a hand's outcome against a dealer hand if it is not yet known."""
        # If the hand is busted it's a loss
        if hand.status == 'Busted':
            self.set_hand_outcome(hand, 'Loss')

        # If the hand is not busted and the dealer's hand is busted it's a win
        elif dealer_hand.status == 'Busted':
            self.set_hand_outcome(hand, 'Win')

        # If neither gambler nor dealer hand is busted, compare totals to determine wins and losses.
        else:
            hand_total = hand.final_total()
            dealer_hand_total = dealer_hand.final_total()

            if hand_total > dealer_hand_total:
                self.set_hand_outcome(hand, 'Win')
            elif hand_total == dealer_hand_total:
                self.set_hand_outcome(hand, 'Push')
            else:
                self.set_hand_outcome(hand, 'Loss')

    def settle_hand(self, hand):
        """Settle any outstanding wagers on a hand (relative to the dealer's hand)."""
        # Determine the outcome of the hand against the dealer's if the outcome is unknown
        if not hand.outcome:
            self.determine_hand_outcome(hand, self.dealer.hand)

        # Perform payout based on the hand outcome
        if hand.outcome == 'Win':
            if hand.status == 'Blackjack' or hand.final_total() == 21:
                self.pay_out_hand(hand, 'blackjack')
            else:
                self.pay_out_hand(hand, 'wager')

        elif hand.outcome == 'Push':
            self.pay_out_hand(hand, 'push')

        elif hand.outcome == 'Even Money':
            self.pay_out_hand(hand, 'wager')

        elif hand.outcome == 'Insurance Win':
            self.pay_out_hand(hand, 'insurance')

        elif hand.outcome == 'Loss':
            self.add_activity(f"Hand {hand.hand_number}: Forfeiting hand wager of {money_format(hand.wager)}.")

        elif hand.outcome == 'Surrender':
            self.add_activity(f"Hand {hand.hand_number}: Surrendered. Half of the wager is forfeited.")

        else:
            raise ValueError(f"Unhandled hand outcome: {hand.outcome}")

    def settle_up(self):
        """For each of the gambler's hands, settle wagers against the dealer's hand."""
        for hand in self.gambler.hands:
            self.settle_hand(hand)

    def track_metrics(self):
        """Update the tracked metrics with the current turn's data."""
        # Track gambler hand metrics
        for hand in self.gambler.hands:
            self.metric_tracker.process_gambler_hand(hand)

        # Track dealer hand metrics
        self.metric_tracker.process_dealer_hand(self.dealer.hand)

        # Track gambler's bankroll through time
        self.metric_tracker.append_bankroll(self.gambler.bankroll)

    def finalize_turn(self):
        """Clean up the current turn in preparation for the next turn."""
        # Render the final status of the turn if applicable.
        if self.verbose:
            self.render()

        # Update tracked metrics
        self.track_metrics()

        # Reset the activity log for the next turn.
        self.activity = []

        # Discard both the gambler and the dealer's hands.
        self.gambler.discard_hands()
        self.dealer.discard_hand()

        # Reset hide_dealer for the next turn.
        self.hide_dealer = True

        # Pause exectution until the user wants to proceed if applicable.
        if self.verbose:
            input('Press REBET to proceed => ')

    def finalize_game(self):
        """Wrap up the game, rendering analytics and creating graphs if necessary."""
        # Render game over message if applicable
        if self.verbose:
            self.render_game_over()

    def render(self):
        """Print out the entire game (comprised of table, activity log, and user action) to the console."""
        clear()  # Clear previous rendering
        self.render_table()
        self.render_activity()
        self.render_action()

    def render_table(self):
        """Print out the players and the hands of cards (if they've been dealt)."""
        # print(header('TABLE'))
        # Print the gambler's name and bankroll
        print(
            f"️Bankroll: {money_format(self.gambler.bankroll)}  |  Auto-Wager: {money_format(self.gambler.auto_wager)}")

        # Print the dealer's hand. If `hide_dealer` is True, don't factor in the dealer's buried card.
        num_dashes = len(self.dealer.name) + 6
        # print(f"{'-'*num_dashes}\n   {self.dealer.name.upper()}   \n{'-'*num_dashes}\n")
        # print(f"️♦️{self.dealer.name.upper()}️")
        if self.dealer.hand:
            print(self.dealer.hand.pretty_format(hide=self.hide_dealer))
        else:
            print('No hand.')

        # Print the gambler's hand(s)
        num_dashes = len(self.gambler.name) + 6

        if self.gambler.hands:
            for hand in self.gambler.hands:
                # Show total-based representation
                total = hand.final_total()
                status_str = f" ({hand.status})" if hand.status else ""
                print(f"Hand {hand.hand_number}: Total {total}{status_str}")
                print(f"Wager: {money_format(hand.wager)}")
                if hand.outcome:
                    print(f"Outcome: {hand.outcome}")
                print()
        else:
            print('No hands.')

    def render_activity(self):
        """Print out the activity log for the current turn."""
        print(header('ACTIVITY'))
        for message in self.activity:
            print(message)

    def render_action(self):
        """Print out the action section that the user interacts with."""
        print(header('ACTION'))
        if self.dealer_playing:
            print('Dealer playing turn...')

    def render_game_over(self):
        """Print out a final summary message once the game has ended."""
        # Show game over message
        print(header('GAME OVER'))

        # Print a final message after the gambler is finished
        if self.gambler.auto_wager == 0 or self.turn == self.max_turns:
            action = f"{self.gambler.name} cashed out with bankroll: {money_format(self.gambler.bankroll)}."
            message = 'Thanks for playing!'
        else:
            action = f"{self.gambler.name} is out of money."
            message = 'Better luck next time!'

        print(f"{action}\n\n{message}")

    def check_for_status_text(self):
        """Check if status text has appeared in the OCR regions"""
        response = input("Has a status text appeared? (BLACKJACK/PUSH/WIN/BUST/SURRENDER) (y/n): ").strip().lower()
        if response == 'y' or response == 'yes':
            status = input("What status appeared? (BLACKJACK/PUSH/WIN/BUST/SURRENDER): ").strip().upper()
            if status in ['BLACKJACK', 'PUSH', 'WIN', 'BUST', 'SURRENDER']:
                return status
        return None

    def handle_immediate_status(self, status_text):
        """Handle the game state based on detected status text"""
        # Create dummy hands if needed
        if not self.gambler.hands:
            self.gambler.hands.append(GamblerHand())
            self.gambler.place_auto_wager()

        hand = self.gambler.first_hand()

        if status_text == 'BLACKJACK':
            self.add_activity("Blackjack detected!")
            self.set_hand_status(hand, 'Blackjack')
            self.set_hand_outcome(hand, 'Win')
        elif status_text == 'PUSH':
            self.add_activity("Push detected!")
            self.set_hand_status(hand, 'Stood')
            self.set_hand_outcome(hand, 'Push')
        elif status_text == 'WIN':
            self.add_activity("Win detected!")
            self.set_hand_status(hand, 'Stood')
            self.set_hand_outcome(hand, 'Win')
        elif status_text == 'BUST':
            self.add_activity("Bust detected!")
            self.set_hand_status(hand, 'Busted')
            self.set_hand_outcome(hand, 'Loss')
        elif status_text == 'SURRENDER':
            self.add_activity("Surrender detected!")
            self.set_hand_status(hand, 'Surrendered')
            self.set_hand_outcome(hand, 'Surrender')

        # Add dealer hand if needed
        if not self.dealer.hand:
            # Create a dealer hand with a dummy card
            dummy_card = Card("Spades", "Dummy", 10)
            self.dealer.hand = DealerHand(cards=[dummy_card])