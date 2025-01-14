import numpy as np
from scipy.stats import linregress

# Data arrays
delayed_test_scores = np.array([2.67, 3.3, 3.0])
questionnaire_scores = np.array([3.0, 3.5, 2.9])

# Calculate Pearson correlation coefficient
correlation_coefficient = np.corrcoef(delayed_test_scores, questionnaire_scores)[0, 1]

# Perform linear regression
slope, intercept, r_value, p_value, std_err = linregress(questionnaire_scores, delayed_test_scores)

# Calculate R-squared
r_squared = r_value ** 2

# Output results
print("Correlation Coefficient (r):", correlation_coefficient)
print("Regression Slope:", slope)
print("Regression Intercept:", intercept)
print("R-squared:", r_squared)
print("P-value:", p_value)