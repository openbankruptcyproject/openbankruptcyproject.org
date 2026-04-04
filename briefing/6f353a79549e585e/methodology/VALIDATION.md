# Validation Guide

## 1328(f) Reproduction
1. Download FJC IDB main + supplementary files (free)
2. Join on case ID
3. Filter to Ch.13 with discharge
4. Calculate gap between prior discharge and current filing
5. Flag cases within bar period (4yr Ch.7/11/12, 2yr Ch.13)
6. Expected: ~391,951 cases (27.4%)

## Opposition Rate Reproduction
1. Download PACER dockets for target firm (iQuery attorney search)
2. Run opposition_rate.py
3. Compare response counts against manual spot-check
