from app.models import RollingStats, RatingBreakdown

class RatingEngine:
    @staticmethod
    def calculate_rating(
        rolling: RollingStats,
        expense_ratio: float,
        aum: float,
        precalculated_5y: float
    ) -> RatingBreakdown:
        """
        Calculates a multi-factor score out of 10.0:
        1. 5Y Rolling Avg Return: 3.5 points (mean CAGR only, no min/max downside)
        2. 5Y Trailing Return: 2.0 points (precalculated point-to-point return)
        3. Expense Ratio (TER): 2.0 points
        4. Consistency & Volatility: 1.5 points (Prob >12% 1.0 + Low Std Dev 0.5)
        5. AUM Scale Factor: 1.0 point (Lesser weightage)
        """
        # 1. 5Y Rolling Avg Return Score (3.5 points max)
        mean_cagr = rolling.mean
        if mean_cagr >= 28.0:
            rolling_score = 3.5
        elif mean_cagr >= 24.0:
            rolling_score = 3.0 + 0.5 * ((mean_cagr - 24.0) / 4.0)
        elif mean_cagr >= 20.0:
            rolling_score = 2.4 + 0.6 * ((mean_cagr - 20.0) / 4.0)
        elif mean_cagr >= 16.0:
            rolling_score = 1.8 + 0.6 * ((mean_cagr - 16.0) / 4.0)
        elif mean_cagr >= 12.0:
            rolling_score = 1.2 + 0.6 * ((mean_cagr - 12.0) / 4.0)
        else:
            rolling_score = max(0.1, 1.2 * (mean_cagr / 12.0))
        rolling_score = round(rolling_score, 2)

        # 2. Historical Precalculated 5Y Trailing Return (2.0 points max)
        p5 = precalculated_5y if precalculated_5y is not None else 0.0
        if p5 >= 22.0:
            hist_score = 2.0
        elif p5 >= 18.0:
            hist_score = 1.6 + 0.4 * ((p5 - 18.0) / 4.0)
        elif p5 >= 14.0:
            hist_score = 1.2 + 0.4 * ((p5 - 14.0) / 4.0)
        elif p5 >= 10.0:
            hist_score = 0.8 + 0.4 * ((p5 - 10.0) / 4.0)
        else:
            hist_score = max(0.2, 0.8 * (p5 / 10.0) if p5 > 0 else 0.1)
        hist_score = round(hist_score, 2)

        # 3. Expense Ratio (TER) Score (2.0 points max)
        ter = expense_ratio if expense_ratio > 0 else 1.2
        if ter <= 0.70:
            ter_score = 2.0
        elif ter <= 0.85:
            ter_score = 1.7 + 0.3 * ((0.85 - ter) / 0.15)
        elif ter <= 1.05:
            ter_score = 1.3 + 0.4 * ((1.05 - ter) / 0.20)
        elif ter <= 1.35:
            ter_score = 0.9 + 0.4 * ((1.35 - ter) / 0.30)
        elif ter <= 1.70:
            ter_score = 0.5 + 0.4 * ((1.70 - ter) / 0.35)
        elif ter <= 2.20:
            ter_score = 0.25 + 0.25 * ((2.20 - ter) / 0.50)
        else:
            ter_score = 0.1
        ter_score = round(ter_score, 2)

        # 4. Consistency & Volatility (1.5 points max)
        # a) Probability of beating 12% CAGR hurdle (1.0 pt)
        p12 = rolling.prob_above_12
        if p12 >= 95.0:
            prob_score = 1.0
        elif p12 >= 85.0:
            prob_score = 0.8 + 0.2 * ((p12 - 85.0) / 10.0)
        elif p12 >= 70.0:
            prob_score = 0.6 + 0.2 * ((p12 - 70.0) / 15.0)
        elif p12 >= 50.0:
            prob_score = 0.35 + 0.25 * ((p12 - 50.0) / 20.0)
        else:
            prob_score = max(0.1, 0.35 * (p12 / 50.0))

        # b) Volatility / Std Dev (0.5 pt, softened so high-growth volatility isn't over-penalized)
        std = rolling.std_dev
        if std <= 5.0:
            std_score = 0.5
        elif std <= 7.0:
            std_score = 0.4 + 0.1 * ((7.0 - std) / 2.0)
        elif std <= 9.0:
            std_score = 0.3 + 0.1 * ((9.0 - std) / 2.0)
        elif std <= 11.0:
            std_score = 0.2 + 0.1 * ((11.0 - std) / 2.0)
        else:
            std_score = 0.15

        consistency_score = round(prob_score + std_score, 2)

        # 5. AUM Scale Factor (1.0 point max) - lesser weightage
        if aum >= 20000.0:
            aum_score = 1.0
        elif aum >= 10000.0:
            aum_score = 0.88 + 0.12 * ((aum - 10000.0) / 10000.0)
        elif aum >= 5000.0:
            aum_score = 0.74 + 0.14 * ((aum - 5000.0) / 5000.0)
        elif aum >= 2000.0:
            aum_score = 0.58 + 0.16 * ((aum - 2000.0) / 3000.0)
        elif aum >= 1000.0:
            aum_score = 0.42 + 0.16 * ((aum - 1000.0) / 1000.0)
        else:
            aum_score = max(0.2, 0.42 * (aum / 1000.0))
        aum_score = round(aum_score, 2)

        total = round(rolling_score + ter_score + consistency_score + aum_score + hist_score, 1)
        total = min(10.0, max(1.0, total))

        if total >= 9.0:
            label = "Elite (Tier 1)"
        elif total >= 8.0:
            label = "Excellent"
        elif total >= 7.0:
            label = "Good"
        elif total >= 5.5:
            label = "Moderate"
        else:
            label = "Underperforming / High Cost"

        return RatingBreakdown(
            rolling_return_score=rolling_score,
            expense_ratio_score=ter_score,
            consistency_score=consistency_score,
            aum_score=aum_score,
            historical_return_score=hist_score,
            total_rating=total,
            rating_label=label
        )
