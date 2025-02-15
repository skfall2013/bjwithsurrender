from statistics import mean
from textwrap import dedent
import matplotlib.pyplot as plt
from blackjack.display_utils import money_format, pct_format, zero_division_pct

def slice_label(percent, all_vals):
    """
    Create a pie chart slice label of the form `x% (absolute count)` (e.g. --> 45.3% (153) ).
    Note that this function was ripped from the matplotlib documentation on the subject.
    """
    absolute = int(percent / 100.0 * sum(all_vals))
    return "{:.1f}%\n({:d})".format(percent, absolute)

class MultiGameAnalyzer:
    """Class for running basic analytics on tracked metrics for a multiple games."""

    def __init__(self, metric_trackers):
        # All games have the same initial bankroll. Grab it from the first game.
        self.initial_bankroll = metric_trackers[0].bankroll_progression[0]

        (self.wins, self.losses, self.pushes, self.insurance_wins, self.insurance_losses,
         self.gambler_blackjacks, self.dealer_blackjacks, self.final_bankrolls,
         self.winning_streaks, self.losing_streaks) = self._aggregate_metrics(metric_trackers)

    @staticmethod
    def _calculate_streaks(wins_losses):
        winning_streaks = []
        losing_streaks = []
        current_winning_streak = 0
        current_losing_streak = 0

        for result in wins_losses:
            if result == 'win':
                if current_losing_streak > 0:
                    losing_streaks.append(current_losing_streak)
                    current_losing_streak = 0
                current_winning_streak += 1
            elif result == 'loss':
                if current_winning_streak > 0:
                    winning_streaks.append(current_winning_streak)
                    current_winning_streak = 0
                current_losing_streak += 1
            else:
                if current_winning_streak > 0:
                    winning_streaks.append(current_winning_streak)
                    current_winning_streak = 0
                if current_losing_streak > 0:
                    losing_streaks.append(current_losing_streak)
                    current_losing_streak = 0

        if current_winning_streak > 0:
            winning_streaks.append(current_winning_streak)
        if current_losing_streak > 0:
            losing_streaks.append(current_losing_streak)

        return winning_streaks, losing_streaks

    @staticmethod
    def _aggregate_metrics(metric_trackers):
        # Gross metric counts
        wins = 0
        losses = 0
        pushes = 0
        insurance_wins = 0
        insurance_losses = 0
        gambler_blackjacks = 0
        dealer_blackjacks = 0

        # Final bankrolls
        final_bankrolls = []

        # Track winning and losing streaks
        all_wins_losses = []

        # Process each MetricTracker
        for mt in metric_trackers:
            wins += mt.wins
            losses += mt.losses
            pushes += mt.pushes
            insurance_wins += mt.insurance_wins
            insurance_losses += mt.insurance_losses
            gambler_blackjacks += mt.gambler_blackjacks
            dealer_blackjacks += mt.dealer_blackjacks
            final_bankrolls.append(mt.bankroll_progression[-1])
            all_wins_losses.extend(mt.wins_losses)  # Assuming `wins_losses` is a list of 'win' or 'loss' strings

        winning_streaks, losing_streaks = MultiGameAnalyzer._calculate_streaks(all_wins_losses)

        return wins, losses, pushes, insurance_wins, insurance_losses, gambler_blackjacks, dealer_blackjacks, final_bankrolls, winning_streaks, losing_streaks

    def print_summary(self):
        """Print a simple summary of analyzed results."""
        # --- Hand Outcomes ---
        total_hands = sum([self.wins, self.losses, self.pushes,
                           self.insurance_wins])  # Note that insurance losses are not a final outcome of a hand!
        hand_win_pct = zero_division_pct(self.wins, total_hands)
        hand_loss_pct = zero_division_pct(self.losses, total_hands)
        hand_push_pct = zero_division_pct(self.pushes, total_hands)
        hand_insurance_win_pct = zero_division_pct(self.insurance_wins, total_hands)

        # --- Blackjacks ---
        total_blackjacks = self.gambler_blackjacks + self.dealer_blackjacks
        bj_gambler_pct = zero_division_pct(self.gambler_blackjacks, total_blackjacks)
        bj_dealer_pct = zero_division_pct(self.dealer_blackjacks, total_blackjacks)

        # --- Insurance ---
        total_insurance = self.insurance_wins + self.insurance_losses
        ins_win_pct = zero_division_pct(self.insurance_wins, total_insurance)
        ins_loss_pct = zero_division_pct(self.insurance_losses, total_insurance)

        # --- Bankroll ---
        winnings_gross_avg = mean(self.final_bankrolls) - self.initial_bankroll
        winnings_pct_avg = zero_division_pct(winnings_gross_avg, self.initial_bankroll)

        # --- Winning Streaks ---
        winning_streaks = self.winning_streaks
        winning_streak_counts = {streak: winning_streaks.count(streak) for streak in set(winning_streaks)}

        # --- Losing Streaks ---
        losing_streaks = self.losing_streaks
        losing_streak_counts = {streak: losing_streaks.count(streak) for streak in set(losing_streaks)}

        # Return the formatted summary string
        print(dedent(f"""\
            --- Hand Outcomes ---

            Total Hands: {total_hands}

            Wins: {self.wins} ({pct_format(hand_win_pct)})
            Losses: {self.losses} ({pct_format(hand_loss_pct)})
            Pushes: {self.pushes} ({pct_format(hand_push_pct)})
            Insurance Wins: {self.insurance_wins} ({pct_format(hand_insurance_win_pct)})

            --- Blackjacks ---

            Total Blackjacks: {total_blackjacks}

            Player Blackjacks: {self.gambler_blackjacks} ({pct_format(bj_gambler_pct)})
            Dealer Blackjacks: {self.dealer_blackjacks} ({pct_format(bj_dealer_pct)})

            --- Insurance ---

            Total Bets: {total_insurance}

            Wins: {self.insurance_wins} ({pct_format(ins_win_pct)})
            Losses: {self.insurance_losses} ({pct_format(ins_loss_pct)})

            --- Bankroll ---

            Avg Winnings: {money_format(winnings_gross_avg)} ({pct_format(winnings_pct_avg)})

            Max Bankroll: {money_format(max(self.final_bankrolls))}
            Min Bankroll: {money_format(min(self.final_bankrolls))}
            Avg Bankroll: {money_format(mean(self.final_bankrolls))}

            --- Winning Streaks ---

            {winning_streak_counts}

            --- Losing Streaks ---

            {losing_streak_counts}

            """)
              )

    def create_plots(self):
        """Create charts summarizing the tracked metric data."""
        # Create a figure to hold the plots (called "axes")
        fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=(10, 20))  # Adjust the figure size

        # Axes 1: Final Bankroll Distribution (Histogram)
        ax1.hist(self.final_bankrolls)
        ax1.set_xlabel('Final Bankroll ($)')
        ax1.set_ylabel('Count')
        ax1.set_title('Final Bankrolls')

        # Axes 2: Hand Outcome Breakdown (pie chart)
        data = []
        labels = []
        for metric, label in [
            (self.wins, 'Wins'), (self.losses, 'Losses'), (self.pushes, 'Pushes'),
            (self.insurance_wins, 'Insurance Wins')
        ]:
            if metric > 0:
                data.append(metric)
                labels.append(label)

        wedges, _, _ = ax2.pie(data, autopct=lambda pct: slice_label(pct, data), textprops=dict(color="w"))
        ax2.legend(wedges, labels, title="Outcomes", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
        ax2.set_title('Hand Outcomes')
        ax2.axis('equal')

        # Axes 3: Winning Streaks (Bar chart)
        winning_streaks = self.winning_streaks
        winning_streak_counts = {streak: winning_streaks.count(streak) for streak in set(winning_streaks)}
        bars = ax3.bar(winning_streak_counts.keys(), winning_streak_counts.values())
        ax3.set_xlabel('Winning Streak Length')
        ax3.set_ylabel('Frequency')
        ax3.set_title('Winning Streaks')

        # Add frequency labels on top of each bar
        for bar in bars:
            height = bar.get_height()
            ax3.annotate(f'{height}',
                         xy=(bar.get_x() + bar.get_width() / 2, height),
                         xytext=(0, 3),  # 3 points vertical offset
                         textcoords="offset points",
                         ha='center', va='bottom')

        # Axes 4: Losing Streaks (Bar chart)
        losing_streaks = self.losing_streaks
        losing_streak_counts = {streak: losing_streaks.count(streak) for streak in set(losing_streaks)}
        bars = ax4.bar(losing_streak_counts.keys(), losing_streak_counts.values())
        ax4.set_xlabel('Losing Streak Length')
        ax4.set_ylabel('Frequency')
        ax4.set_title('Losing Streaks')

        # Add frequency labels on top of each bar
        for bar in bars:
            height = bar.get_height()
            ax4.annotate(f'{height}',
                         xy=(bar.get_x() + bar.get_width() / 2, height),
                         xytext=(0, 3),  # 3 points vertical offset
                         textcoords="offset points",
                         ha='center', va='bottom')

        # Avoid plot label overlap
        plt.tight_layout()
        plt.show()