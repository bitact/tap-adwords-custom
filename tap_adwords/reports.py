VERIFIED_REPORTS_NO_DATE = ['CAMPAIGN_NEGATIVE_KEYWORDS_PERFORMANCE_REPORT']

VERIFIED_REPORTS = [
    'ACCOUNT_PERFORMANCE_REPORT',
    'ADGROUP_PERFORMANCE_REPORT',
    # 'AD_CUSTOMIZERS_FEED_ITEM_REPORT',
    'AD_PERFORMANCE_REPORT',
    'AGE_RANGE_PERFORMANCE_REPORT',
    'AUDIENCE_PERFORMANCE_REPORT',
    # 'AUTOMATIC_PLACEMENTS_PERFORMANCE_REPORT',
    # 'BID_GOAL_PERFORMANCE_REPORT',
    #'BUDGET_PERFORMANCE_REPORT',                       -- does NOT allow for querying by date range
    'CALL_METRICS_CALL_DETAILS_REPORT',
    #'CAMPAIGN_AD_SCHEDULE_TARGET_REPORT',
    #'CAMPAIGN_CRITERIA_REPORT',
    #'CAMPAIGN_GROUP_PERFORMANCE_REPORT',
    #'CAMPAIGN_LOCATION_TARGET_REPORT',
    #'CAMPAIGN_NEGATIVE_KEYWORDS_PERFORMANCE_REPORT',   -- does NOT allow for querying by date range
    #'CAMPAIGN_NEGATIVE_LOCATIONS_REPORT',              -- does NOT allow for querying by date range
    #'CAMPAIGN_NEGATIVE_PLACEMENTS_PERFORMANCE_REPORT', -- does NOT allow for querying by date range
    'CAMPAIGN_PERFORMANCE_REPORT',
    #'CAMPAIGN_SHARED_SET_REPORT',                      -- does NOT allow for querying by date range
    'CLICK_PERFORMANCE_REPORT',
    #'CREATIVE_CONVERSION_REPORT',
    'CRITERIA_PERFORMANCE_REPORT',
    'DISPLAY_KEYWORD_PERFORMANCE_REPORT',
    'DISPLAY_TOPICS_PERFORMANCE_REPORT',
    'FINAL_URL_REPORT',
    'GENDER_PERFORMANCE_REPORT',
    'GEO_PERFORMANCE_REPORT',
    #'KEYWORDLESS_CATEGORY_REPORT',
    'KEYWORDLESS_QUERY_REPORT',
    'KEYWORDS_PERFORMANCE_REPORT',
    #'LABEL_REPORT',                                    -- does NOT allow for querying by date range,
    #'PAID_ORGANIC_QUERY_REPORT',
    #'PARENTAL_STATUS_PERFORMANCE_REPORT',
    'PLACEHOLDER_FEED_ITEM_REPORT',
    'PLACEHOLDER_REPORT',
    'PLACEMENT_PERFORMANCE_REPORT',
    #'PRODUCT_PARTITION_REPORT',
    'SEARCH_QUERY_PERFORMANCE_REPORT',
    #'SHARED_SET_CRITERIA_REPORT',                      -- does NOT allow for querying by date range
    #'SHARED_SET_REPORT',                               -- does NOT allow for querying by date range
    #'SHARED_SET_REPORT',
    'SHOPPING_PERFORMANCE_REPORT',
    #'TOP_CONTENT_PERFORMANCE_REPORT',
    #'URL_PERFORMANCE_REPORT',
    #'USER_AD_DISTANCE_REPORT',
    'VIDEO_PERFORMANCE_REPORT',
    #'UNKNOWN'
]

REPORTS_WITH_90_DAY_MAX = ['CLICK_PERFORMANCE_REPORT']

REPORT_TYPE_MAPPINGS = {"Boolean":  {"type": ["null", "boolean"]},
                        "boolean":  {'type': ["null", "boolean"]},
                        "Double":   {"type": ["null", "number"]},
                        "int":      {"type": ["null", "integer"]},
                        "Integer":  {"type": ["null", "integer"]},
                        "long":     {"type": ["null", "integer"]},
                        "Long":     {"type": ["null", "integer"]},
                        "Date":     {"type": ["null", "string"],
                                     "format": "date-time"},
                        "DateTime": {"type": ["null", "string"],
                                     "format": "date-time"},
                        "Money":    {"type": ["null", "integer", "string"]}}