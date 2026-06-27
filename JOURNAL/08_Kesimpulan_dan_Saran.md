# 08 — Conclusion and Recommendations

## V. Conclusion

This study successfully designed, implemented, and evaluated a production-ready two-layer demand forecasting system for UHT milk distribution at PT GS Battery's employee vending facility. The system integrates a machine learning component for monthly aggregate prediction (Layer 1) with a deterministic rule-based component for daily distribution (Layer 2), forming a heterogeneous cascaded architecture that addresses the distinct nature of each forecasting task.

The central finding of this research is that a heterogeneous ML-plus-rule-based architecture significantly outperforms a purely data-driven approach for granular daily distribution forecasting. A comparative experiment using Meta's Prophet model as a pure ML baseline yielded a daily Weighted Absolute Percentage Error (WAPE) of 27%, whereas the rule-based Smart Event Classifier v2.2 achieved a WAPE of 3.99% — a reduction of more than 85%. This result suggests that in operational environments with strong, interpretable seasonal signals such as weekly shift cycles, national holidays, and religious observance periods, explicit domain knowledge encoded as classification rules can be more effective and more reliable than learned distributional patterns alone.

At the aggregate monthly level, the XGBoost V6 model (Layer 1) demonstrated strong generalization capability. A walk-forward backtest over four consecutive non-Ramadan months yielded a mean MAPE of 3.34%, and the out-of-sample forward test for Q1 2026 confirmed this performance on fully unseen data, with January 2026 producing an error of only 0.68%. These results place the system well within the threshold conventionally required for production deployment.

A technically novel contribution of this work is the Ramadan Lag Skipper — a dual-mode temporal feature engineering mechanism that dynamically bypasses Ramadan months when computing lag features for any prediction period from January 2026 onward. Without this mechanism, the model's predictive features would be contaminated by anomalous near-zero consumption values from Ramadan, leading to distorted growth rates and trend slopes. The Lag Skipper effectively decouples the model's temporal reference frame from the Islamic calendar cycle, a consideration with direct relevance to demand forecasting in Muslim-majority industrial settings across Southeast Asia.

The Step 9 Business Logic Fallback further reinforces the system's reliability under extreme conditions. When a target month is identified as having ten or fewer productive working days — the signature of a full Ramadan month — the system automatically bypasses the XGBoost prediction in favor of a heuristic derived from historical average daily consumption. This *graceful degradation* strategy yielded an error of only 1.75% for March 2026, a month with only two productive working days.

Finally, the system operates with full daily automation orchestrated by a single pipeline entry point, incorporating three layers of data validation (SATPAM) that prevent forecasting from proceeding on incomplete or unsynchronized data. The overall evaluation score of 84 out of 100 across eleven weighted criteria confirms the system's readiness for long-term autonomous production operation.

---

## VI. Recommendations

While the system has demonstrated strong performance across all primary evaluation criteria, several dimensions remain open for further development. The following recommendations are directed exclusively at advancing the research and improving the system in future work.

The first and most impactful area for further research concerns per-variant prediction accuracy. Although the system predicts aggregate monthly demand with high accuracy (MAPE 3.34%), prediction at the individual product variant level — Chocolate, Mocha, Original, and Strawberry — retains errors in the range of 15–18%. This residual error is partly attributable to the stochastic nature of individual consumer choice, which is inherently non-deterministic at the daily level. Future work could explore whether employee-level preference data, shift composition data, or cross-variant correlation features can reduce this variance, or alternatively, whether probabilistic forecasting methods such as quantile regression forests or conformal prediction intervals can provide actionable uncertainty bounds at the variant level.

The second recommendation addresses the system's lack of architectural flexibility toward new distributional entities. The current implementation encodes variant membership as four fixed binary dummy variables and maps shift codes to a predefined taxonomy. Consequently, introducing a new milk variant or a new shift type would require manual feature schema changes and full model retraining. Future research should investigate a generalized entity embedding approach — for example, learned variant embeddings rather than hard-coded one-hot encoding — that would allow the system to accommodate new variants or operational configurations without architectural modification.

Third, the historical depth of Ramadan data represents a meaningful constraint on the model's robustness to inter-annual variation in Islamic calendar effects. The training dataset covers three Ramadan cycles (2023, 2024, 2025), which is sufficient to establish the fundamental behavioral pattern but insufficient to capture the full range of variation driven by the progressive calendar shift of approximately eleven days per year. A dataset spanning at least five Ramadan cycles is recommended as the target for achieving statistically stable lag-skip and factor-calibration estimates.

Fourth, the current system relies exclusively on vending machine transaction data as its sole input source. Access to complementary institutional data — such as employee headcount records, shift scheduling logs, or facility shutdown calendars maintained outside the operational calendar database — was not available for this study due to data governance constraints. Future research collaboration with relevant departments should explore whether such data can be incorporated under appropriate privacy and authorization frameworks, as these features are theoretically informative for demand prediction.

Fifth, the system currently produces only point estimates for each predicted period, without any associated uncertainty quantification. For inventory procurement decisions, a point estimate alone is insufficient to optimize safety stock levels in a principled way. A natural extension of this work would be the integration of prediction intervals — for example, 80% or 95% coverage intervals derived from quantile regression or bootstrapped XGBoost ensembles — enabling the procurement team to make risk-aware stocking decisions that explicitly account for forecast uncertainty.

Sixth, the behavioral parameters governing the Smart Event Classifier — including the Ramadan consumption factor, the day-of-week share distribution, and the hangover and holiday weighting factors — are calibrated once from historical data and remain static thereafter. Over time, structural changes in the workforce composition, shift rotation policies, or facility operating hours may cause these parameters to drift away from true underlying patterns without any automated detection mechanism. Future work should develop a periodic recalibration protocol, or alternatively an online learning component, that detects distributional shifts in daily consumption patterns and updates the classifier's parameters accordingly.

---

*Document created: June 2026*
*Language: English (Academic Journal Format)*
*Status: Ready for inclusion in manuscript draft*
