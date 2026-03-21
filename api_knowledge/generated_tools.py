# api_knowledge/generated_tools.py
"""Auto-generated Tripletex API tool definitions.

Generated from OpenAPI spec. 344 tools across 4 HTTP methods.
DO NOT EDIT MANUALLY — regenerate with: python scripts/generate_tools.py
"""

GENERATED_TOOLS = [
  {
    "name": "activity_get",
    "description": "Find activity by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "activity_list_post_list",
    "description": "Add multiple activities.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "activity_for_time_sheet_get_for_time_sheet",
    "description": "Find applicable time sheet activities for an employee on a specific day.",
    "input_schema": {
      "type": "object",
      "properties": {
        "projectId": {
          "type": "integer",
          "format": "int64",
          "description": "Project ID"
        },
        "employeeId": {
          "type": "integer",
          "format": "int64",
          "description": "Employee ID. Defaults to ID of token owner."
        },
        "date": {
          "type": "string",
          "description": "yyyy-MM-dd. Defaults to today."
        },
        "filterExistingHours": {
          "type": "boolean",
          "default": true,
          "description": "Whether to filter out activities that have registered hours."
        },
        "query": {
          "type": "string",
          "description": "Containing"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "projectId"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "activity_search",
    "description": "Find activities corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "List of IDs"
        },
        "name": {
          "type": "string",
          "description": "Containing"
        },
        "number": {
          "type": "string",
          "description": "Equals"
        },
        "description": {
          "type": "string",
          "description": "Containing"
        },
        "isProjectActivity": {
          "type": "boolean",
          "description": "Equals"
        },
        "isGeneral": {
          "type": "boolean",
          "description": "Equals"
        },
        "isChargeable": {
          "type": "boolean",
          "description": "Equals"
        },
        "isTask": {
          "type": "boolean",
          "description": "Equals"
        },
        "isInactive": {
          "type": "boolean",
          "description": "Equals"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "activity_post",
    "description": "Add activity.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "delivery_address_get",
    "description": "Get address by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "delivery_address_put",
    "description": "Update address.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "delivery_address_search",
    "description": "Find addresses corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "List of IDs"
        },
        "addressLine1": {
          "type": "string",
          "description": "List of IDs"
        },
        "addressLine2": {
          "type": "string",
          "description": "List of IDs"
        },
        "postalCode": {
          "type": "string",
          "description": "List of IDs"
        },
        "city": {
          "type": "string",
          "description": "List of IDs"
        },
        "name": {
          "type": "string",
          "description": "List of IDs"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "asset_balance_accounts_sum_balance_accounts_sum",
    "description": "Get balanceAccountsSum.",
    "input_schema": {
      "type": "object",
      "properties": {
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "asset_can_delete_can_delete",
    "description": "Validate delete asset",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "asset_get",
    "description": "Get asset by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "asset_put",
    "description": "Update asset.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "asset_delete",
    "description": "Delete asset.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "asset_list_post_list",
    "description": "Create several assets.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "asset_delete_import_delete_import",
    "description": "[BETA] Delete most recent assets import.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "asset_delete_starting_balance_delete_starting_balance",
    "description": "[BETA] Delete the asset starting balance.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "asset_assets_exist_get_assets_exist",
    "description": "Get if AssetOverview details is empty.",
    "input_schema": {
      "type": "object",
      "properties": {
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "asset_postings_get_postings",
    "description": "Get postings associated with asset",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "dateFrom": {
          "type": "string",
          "description": "yyyy-MM-dd. Defaults to today."
        },
        "dateToExclusive": {
          "type": "string",
          "description": "yyyy-MM-dd. Defaults to today."
        },
        "fields": {
          "type": "string",
          "default": "*",
          "description": "Fields filter pattern"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "asset_search",
    "description": "Find assets corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "List of IDs"
        },
        "name": {
          "type": "string",
          "description": "Containing"
        },
        "description": {
          "type": "string",
          "description": "Containing"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "asset_post",
    "description": "Create one asset.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "asset_duplicate_post_duplicate",
    "description": "Create copy of one asset",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "asset_upload_upload",
    "description": "[BETA] Upload Excel file with Assets in the standard Tripletex defined format.",
    "input_schema": {
      "type": "object",
      "properties": {
        "isPreview": {
          "type": "boolean",
          "description": "Is the import a preview, or a real import."
        },
        "startDate": {
          "type": "string",
          "description": "Start date for asset registry. Should always be on the first day of the year."
        }
      },
      "required": [
        "isPreview",
        "startDate"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "balance_sheet_search",
    "description": "Get balance sheet (saldobalanse).",
    "input_schema": {
      "type": "object",
      "properties": {
        "dateFrom": {
          "type": "string",
          "description": "Format is yyyy-MM-dd (from and incl.)."
        },
        "dateTo": {
          "type": "string",
          "description": "Format is yyyy-MM-dd (to and excl.)."
        },
        "accountNumberFrom": {
          "type": "integer",
          "format": "int32",
          "description": "From and including"
        },
        "accountNumberTo": {
          "type": "integer",
          "format": "int32",
          "description": "To and excluding"
        },
        "customerId": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID for filtering"
        },
        "employeeId": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID for filtering"
        },
        "departmentId": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID for filtering"
        },
        "projectId": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID for filtering"
        },
        "includeSubProjects": {
          "type": "boolean",
          "default": false,
          "description": "Should sub projects of the given project be included"
        },
        "includeActiveAccountsWithoutMovements": {
          "type": "boolean",
          "default": false,
          "description": "Should active accounts with no movements be included"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "dateFrom",
        "dateTo"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "bank_reconciliation_adjustment_adjustment",
    "description": "Add an adjustment to reconciliation by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "bank_reconciliation_closed_with_unmatched_transactions_closed_with_unmatched_transactions",
    "description": "Get the last closed reconciliation with unmached transactions by account ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "accountId": {
          "type": "integer",
          "format": "int64",
          "description": "Account ID"
        },
        "start": {
          "type": "string",
          "description": "Format is yyyy-MM-dd"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "accountId"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "bank_reconciliation_transactions_unmatchedcsv_csv_transactions",
    "description": "Get all unmatched transactions in csv format",
    "input_schema": {
      "type": "object",
      "properties": {
        "reconciliationId": {
          "type": "integer",
          "format": "int64",
          "description": "ID for reconciliation"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "bank_reconciliation_get",
    "description": "Get bank reconciliation.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "bank_reconciliation_put",
    "description": "Update a bank reconciliation.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "bank_reconciliation_delete",
    "description": "Delete bank reconciliation by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "bank_reconciliation_last_last",
    "description": "Get the last created reconciliation by account ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "accountId": {
          "type": "integer",
          "format": "int64",
          "description": "Account ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "accountId"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "bank_reconciliation_last_closed_last_closed",
    "description": "Get last closed reconciliation by account ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "accountId": {
          "type": "integer",
          "format": "int64",
          "description": "Account ID"
        },
        "after": {
          "type": "string",
          "description": "Format is yyyy-MM-dd"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "accountId"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "bank_reconciliation_search",
    "description": "Find bank reconciliation corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "List of IDs"
        },
        "accountingPeriodId": {
          "type": "string",
          "description": "List of IDs"
        },
        "accountId": {
          "type": "string",
          "description": "List of IDs"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "bank_reconciliation_post",
    "description": "Post a bank reconciliation.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "bank_reconciliation_match_count_count",
    "description": "Get the total number of matches",
    "input_schema": {
      "type": "object",
      "properties": {
        "bankReconciliationId": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "bankReconciliationId"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "bank_reconciliation_match_get",
    "description": "Get bank reconciliation match by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "bank_reconciliation_match_put",
    "description": "Update a bank reconciliation match by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "bank_reconciliation_match_delete",
    "description": "Delete a bank reconciliation match by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "bank_reconciliation_match_search",
    "description": "Find bank reconciliation match corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "List of IDs"
        },
        "bankReconciliationId": {
          "type": "string",
          "description": "List of bank reconciliation IDs"
        },
        "count": {
          "type": "integer",
          "format": "int32",
          "default": 5000,
          "description": "Number of elements to return"
        },
        "approved": {
          "type": "boolean",
          "description": "Approved or unapproved matches"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "bank_reconciliation_match_post",
    "description": "Create a bank reconciliation match.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "bank_reconciliation_match_query_query",
    "description": "[INTERNAL] Wildcard search.",
    "input_schema": {
      "type": "object",
      "properties": {
        "bankReconciliationId": {
          "type": "integer",
          "format": "int64",
          "description": "The bank reconciliation id"
        },
        "approved": {
          "type": "boolean",
          "description": "Approved or unapproved matches"
        },
        "count": {
          "type": "integer",
          "format": "int32",
          "description": "Number of elements to return"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "bank_reconciliation_match_suggest_suggest",
    "description": "Suggest matches for a bank reconciliation by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "bankReconciliationId": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "bankReconciliationId"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "bank_reconciliation_matches_counter_get",
    "description": "[BETA] Get number of matches since last page access.",
    "input_schema": {
      "type": "object",
      "properties": {
        "bankReconciliationId": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "bankReconciliationId"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "bank_reconciliation_matches_counter_post",
    "description": "[BETA] Reset the number of matches after the page has been accessed.",
    "input_schema": {
      "type": "object",
      "properties": {
        "bankReconciliationId": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "bankReconciliationId"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "company_with_login_access_get_with_login_access",
    "description": "Returns client customers (with accountant/auditor relation) where the current user has login access (proxy login).",
    "input_schema": {
      "type": "object",
      "properties": {
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "company_get",
    "description": "Find company by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "company_divisions_get_divisions",
    "description": "[DEPRECATED] Find divisions.",
    "input_schema": {
      "type": "object",
      "properties": {
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "company_put",
    "description": "Update company information.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "contact_get",
    "description": "Get contact by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "contact_put",
    "description": "Update contact.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "contact_list_post_list",
    "description": "Create multiple contacts.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "contact_list_delete_by_ids",
    "description": "[BETA] Delete multiple contacts.",
    "input_schema": {
      "type": "object",
      "properties": {
        "ids": {
          "type": "string",
          "description": "ID of the elements"
        }
      },
      "required": [
        "ids"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "contact_search",
    "description": "Find contacts corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "List of IDs"
        },
        "firstName": {
          "type": "string",
          "description": "Containing"
        },
        "lastName": {
          "type": "string",
          "description": "Containing"
        },
        "email": {
          "type": "string",
          "description": "Containing"
        },
        "customerId": {
          "type": "string",
          "description": "List of IDs"
        },
        "departmentId": {
          "type": "string",
          "description": "List of IDs"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "contact_post",
    "description": "Create contact.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "country_get",
    "description": "Get country by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "country_search",
    "description": "Find countries corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "List of IDs"
        },
        "code": {
          "type": "string",
          "description": "List of IDs"
        },
        "isDisabled": {
          "type": "boolean",
          "description": "Equals"
        },
        "supportedInZtl": {
          "type": "boolean",
          "description": "Equals"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "currency_get",
    "description": "Get currency by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "currency_search",
    "description": "Find currencies corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "List of IDs"
        },
        "code": {
          "type": "string",
          "description": "Currency codes"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "currency_exchange_rate_convert_currency_amount",
    "description": "Returns the amount in the specified currency, where the input amount is in fromCurrency, using the newest exchange rate available for the given date",
    "input_schema": {
      "type": "object",
      "properties": {
        "fromCurrencyID": {
          "type": "integer",
          "format": "int64",
          "description": "From Currency ID"
        },
        "toCurrencyID": {
          "type": "integer",
          "format": "int64",
          "description": "To Currency ID"
        },
        "amount": {
          "type": "number",
          "description": "Amount to be exchanged"
        },
        "date": {
          "type": "string",
          "description": "Voucher date"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "fromCurrencyID",
        "toCurrencyID",
        "amount",
        "date"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "currency_exchange_rate_get_amount_currency",
    "description": "Returns the amount in the company currency, where the input amount is in fromCurrency, using the newest exchange rate available for the given date",
    "input_schema": {
      "type": "object",
      "properties": {
        "fromCurrencyID": {
          "type": "integer",
          "format": "int32",
          "description": "From Currency ID"
        },
        "amount": {
          "type": "number",
          "description": "Amount to be exchanged"
        },
        "date": {
          "type": "string",
          "description": "Voucher date"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "fromCurrencyID",
        "amount",
        "date"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "currency_rate_get_rate",
    "description": "Find currency exchange rate corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Currency id"
        },
        "date": {
          "type": "string",
          "description": "Format is yyyy-MM-dd"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id",
        "date"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "customer_get",
    "description": "Get customer by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "customer_put",
    "description": "Update customer. ",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "customer_delete",
    "description": "[BETA] Delete customer by ID",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "customer_search",
    "description": "Find customers corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "List of IDs"
        },
        "customerAccountNumber": {
          "type": "string",
          "description": "List of customer numbers"
        },
        "organizationNumber": {
          "type": "string",
          "description": "Equals"
        },
        "email": {
          "type": "string",
          "description": "Equals"
        },
        "invoiceEmail": {
          "type": "string",
          "description": "Equals"
        },
        "customerName": {
          "type": "string",
          "description": "Name"
        },
        "phoneNumberMobile": {
          "type": "string",
          "description": "Phone number mobile"
        },
        "isInactive": {
          "type": "boolean",
          "default": false,
          "description": "Equals"
        },
        "accountManagerId": {
          "type": "string",
          "description": "List of IDs"
        },
        "changedSince": {
          "type": "string",
          "description": "Only return elements that have changed since this date and time"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "customer_post",
    "description": "Create customer. Related customer addresses may also be created.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "customer_list_put_list",
    "description": "[BETA] Update multiple customers. Addresses can also be updated.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "customer_list_post_list",
    "description": "[BETA] Create multiple customers. Related supplier addresses may also be created.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "customer_category_get",
    "description": "Find customer/supplier category by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "customer_category_put",
    "description": "Update customer/supplier category.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "customer_category_search",
    "description": "Find customer/supplier categories corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "List of IDs"
        },
        "name": {
          "type": "string",
          "description": "Containing"
        },
        "number": {
          "type": "string",
          "description": "Equals"
        },
        "description": {
          "type": "string",
          "description": "Containing"
        },
        "type": {
          "type": "string",
          "description": "List of IDs"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "customer_category_post",
    "description": "Add new customer/supplier category.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "department_get",
    "description": "Get department by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "department_put",
    "description": "Update department.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "department_delete",
    "description": "Delete department by ID",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "department_search",
    "description": "Find department corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "List of IDs"
        },
        "name": {
          "type": "string",
          "description": "Containing"
        },
        "departmentNumber": {
          "type": "string",
          "description": "Containing"
        },
        "departmentManagerId": {
          "type": "string",
          "description": "List of IDs"
        },
        "isInactive": {
          "type": "boolean",
          "description": "true - return only inactive departments; false - return only active departments; unspecified - return both types"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "department_post",
    "description": "Add new department.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "department_list_put_list",
    "description": "Update multiple departments.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "department_list_post_list",
    "description": "Register new departments.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "department_query_query",
    "description": "Wildcard search.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "List of IDs"
        },
        "query": {
          "type": "string",
          "description": "Containing"
        },
        "count": {
          "type": "integer",
          "format": "int32",
          "default": 25,
          "description": "Number of elements to return"
        },
        "fields": {
          "type": "string",
          "default": "id, name",
          "description": "Fields filter pattern"
        },
        "isInactive": {
          "type": "boolean",
          "description": "true - return only inactive departments; false - return only active departments; unspecified - return both types"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "division_search",
    "description": "Get divisions.",
    "input_schema": {
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "Containing"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "division_post",
    "description": "Create division.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "division_list_put_list",
    "description": "Update multiple divisions.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "division_list_post_list",
    "description": "Create divisions.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "division_put",
    "description": "Update division information.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "employee_get",
    "description": "Get employee by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "employee_put",
    "description": "Update employee.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "employee_list_post_list",
    "description": "Create several employees.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "employee_search",
    "description": "Find employees corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "List of IDs"
        },
        "firstName": {
          "type": "string",
          "description": "Containing"
        },
        "lastName": {
          "type": "string",
          "description": "Containing"
        },
        "employeeNumber": {
          "type": "string",
          "description": "Equals"
        },
        "email": {
          "type": "string",
          "description": "Containing"
        },
        "allowInformationRegistration": {
          "type": "boolean",
          "description": "Equals"
        },
        "includeContacts": {
          "type": "boolean",
          "default": false,
          "description": "Equals"
        },
        "departmentId": {
          "type": "string",
          "description": "List of IDs"
        },
        "onlyProjectManagers": {
          "type": "boolean",
          "description": "Equals"
        },
        "onlyContacts": {
          "type": "boolean",
          "default": false,
          "description": "Equals"
        },
        "assignableProjectManagers": {
          "type": "boolean",
          "description": "Equals"
        },
        "periodStart": {
          "type": "string",
          "description": "Equals"
        },
        "periodEnd": {
          "type": "string",
          "description": "Equals"
        },
        "hasSystemAccess": {
          "type": "boolean",
          "description": "Equals"
        },
        "onlyEmployeeTokens": {
          "type": "boolean",
          "description": "Equals"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "employee_post",
    "description": "Create one employee.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "employee_search_for_employees_and_contacts_search_for_employees_and_contacts",
    "description": "Get employees and contacts by parameters. Include contacts by default.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "List of IDs"
        },
        "firstName": {
          "type": "string",
          "description": "Containing"
        },
        "lastName": {
          "type": "string",
          "description": "Containing"
        },
        "email": {
          "type": "string",
          "description": "Containing"
        },
        "includeContacts": {
          "type": "boolean",
          "default": true,
          "description": "Equals"
        },
        "isInactive": {
          "type": "boolean",
          "description": "Equals"
        },
        "hasSystemAccess": {
          "type": "boolean",
          "description": "Equals"
        },
        "excludeReadOnly": {
          "type": "boolean",
          "description": "Equals"
        },
        "fields": {
          "type": "string",
          "default": "id, employeeNumber, firstName, lastName, email, pictureId",
          "description": "Fields filter pattern"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "employee_employment_get",
    "description": "Find employment by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "employee_employment_put",
    "description": "Update employemnt. ",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "employee_employment_search",
    "description": "Find all employments for employee.",
    "input_schema": {
      "type": "object",
      "properties": {
        "employeeId": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "employee_employment_post",
    "description": "Create employment.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "employee_employment_details_get",
    "description": "Find employment details by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "employee_employment_details_put",
    "description": "Update employment details. ",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "employee_employment_details_search",
    "description": "Find all employmentdetails for employment.",
    "input_schema": {
      "type": "object",
      "properties": {
        "employmentId": {
          "type": "string",
          "description": "List of IDs"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "employee_employment_details_post",
    "description": "Create employment details.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "employee_entitlement_client_client",
    "description": "[BETA] Find all entitlements at client for user.",
    "input_schema": {
      "type": "object",
      "properties": {
        "employeeId": {
          "type": "integer",
          "format": "int64",
          "description": "Employee ID. Defaults to ID of token owner."
        },
        "customerId": {
          "type": "integer",
          "format": "int64",
          "description": "Client ID"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "employee_entitlement_get",
    "description": "Get entitlement by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "employee_entitlement_grant_client_entitlements_by_template_grant_client_entitlements_by_template",
    "description": "[BETA] Update employee entitlements in client account.",
    "input_schema": {
      "type": "object",
      "properties": {
        "employeeId": {
          "type": "integer",
          "format": "int64",
          "description": "Employee ID"
        },
        "customerId": {
          "type": "integer",
          "format": "int64",
          "description": "Client ID"
        },
        "template": {
          "type": "string",
          "enum": [
            "NONE_PRIVILEGES",
            "STANDARD_PRIVILEGES_ACCOUNTANT",
            "STANDARD_PRIVILEGES_AUDITOR",
            "ALL_PRIVILEGES",
            "AGRO_READ_ONLY",
            "AGRO_READ_APPROVE",
            "AGRO_READ_WRITE",
            "AGRO_READ_WRITE_APPROVE",
            "AGRO_PAYROLL_ADMIN",
            "AGRO_PAYROLL_CLERK",
            "AGRO_INVOICE_ADMIN",
            "AGRO_INVOICE_CLERK"
          ],
          "description": "Template"
        },
        "addToExisting": {
          "type": "boolean",
          "default": false,
          "description": "Add template to existing entitlements"
        }
      },
      "required": [
        "employeeId",
        "customerId",
        "template"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "employee_entitlement_grant_entitlements_by_template_grant_entitlements_by_template",
    "description": "[BETA] Update employee entitlements.",
    "input_schema": {
      "type": "object",
      "properties": {
        "employeeId": {
          "type": "integer",
          "format": "int64",
          "description": "Employee ID"
        },
        "template": {
          "type": "string",
          "enum": [
            "NONE_PRIVILEGES",
            "ALL_PRIVILEGES",
            "INVOICING_MANAGER",
            "PERSONELL_MANAGER",
            "ACCOUNTANT",
            "AUDITOR",
            "DEPARTMENT_LEADER"
          ],
          "description": "Template"
        }
      },
      "required": [
        "employeeId",
        "template"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "employee_entitlement_search",
    "description": "Find all entitlements for user.",
    "input_schema": {
      "type": "object",
      "properties": {
        "employeeId": {
          "type": "integer",
          "format": "int64",
          "description": "Employee ID. Defaults to ID of token owner."
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "incoming_invoice_add_payment_add_payment",
    "description": "[BETA] create a payment for voucher/invoice",
    "input_schema": {
      "type": "object",
      "properties": {
        "voucherId": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "voucherId"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "incoming_invoice_get",
    "description": "[BETA] Get an invoice by voucherId",
    "input_schema": {
      "type": "object",
      "properties": {
        "voucherId": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "voucherId"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "incoming_invoice_put",
    "description": "[BETA] update an invoice by voucherId",
    "input_schema": {
      "type": "object",
      "properties": {
        "voucherId": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "sendTo": {
          "type": "string",
          "description": "'inbox' | 'nonPosted' | 'ledger' | null. When null: preserves current state."
        }
      },
      "required": [
        "voucherId"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "incoming_invoice_post",
    "description": "[BETA] create an invoice",
    "input_schema": {
      "type": "object",
      "properties": {
        "sendTo": {
          "type": "string",
          "description": "'inbox' | 'nonPosted' | 'ledger' | null. When null: defaults to 'inbox'."
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "incoming_invoice_search_search",
    "description": "[BETA] Get a list of invoices",
    "input_schema": {
      "type": "object",
      "properties": {
        "voucherId": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "invoiceDateFrom": {
          "type": "string",
          "description": "From and including"
        },
        "invoiceDateTo": {
          "type": "string",
          "description": "To and excluding"
        },
        "invoiceNumber": {
          "type": "string",
          "description": "Equals"
        },
        "vendorId": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "status": {
          "type": "string",
          "default": "ledger",
          "description": "List of invoice status: 'inbox' | 'nonPosted' | 'approval' | 'ledger'. separated by comma. defaults to 'ledger' when null."
        },
        "from": {
          "type": "integer",
          "format": "int64",
          "default": 0,
          "description": "Offset for pagination. Pagination is approximate when filtering by both draft and posted statuses, as the underlying data is fetched from two different sources and merged in memory."
        },
        "count": {
          "type": "integer",
          "format": "int64",
          "default": 1000,
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "inventory_get",
    "description": "Get inventory by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "inventory_put",
    "description": "Update inventory.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "inventory_delete",
    "description": "Delete inventory.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "inventory_search",
    "description": "Find inventory corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "List of IDs"
        },
        "name": {
          "type": "string",
          "description": "Containing"
        },
        "isMainInventory": {
          "type": "boolean",
          "description": "Equals"
        },
        "isInactive": {
          "type": "boolean",
          "description": "Equals"
        },
        "query": {
          "type": "string",
          "description": "Containing"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "inventory_post",
    "description": "Create new inventory.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "inventory_location_get",
    "description": "Get inventory location by ID. Only available for Logistics Basic.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "inventory_location_put",
    "description": "Update inventory location. Only available for Logistics Basic.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "inventory_location_delete",
    "description": "Delete inventory location. Only available for Logistics Basic.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "inventory_location_list_put_list",
    "description": "Update multiple inventory locations. Only available for Logistics Basic.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "inventory_location_list_post_list",
    "description": "Add multiple inventory locations. Only available for Logistics Basic.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "inventory_location_list_delete_by_ids",
    "description": "Delete inventory location. Only available for Logistics Basic.",
    "input_schema": {
      "type": "object",
      "properties": {
        "ids": {
          "type": "string",
          "description": "ID of the elements"
        }
      },
      "required": [
        "ids"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "inventory_location_search",
    "description": "Find inventory locations by inventory ID. Only available for Logistics Basic.",
    "input_schema": {
      "type": "object",
      "properties": {
        "warehouseId": {
          "type": "string",
          "description": "List of IDs"
        },
        "isInactive": {
          "type": "boolean",
          "description": "Equals"
        },
        "name": {
          "type": "string",
          "description": "Containing"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "inventory_location_post",
    "description": "Create new inventory location. Only available for Logistics Basic.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "invoice_create_credit_note_create_credit_note",
    "description": "Creates a new Invoice representing a credit memo that nullifies the given invoice. Updates this invoice and any pre-existing inverse invoice.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Invoice id"
        },
        "date": {
          "type": "string",
          "description": "Credit note date"
        },
        "comment": {
          "type": "string",
          "description": "Comment"
        },
        "creditNoteEmail": {
          "type": "string",
          "description": "The credit note will not be sent if the customer send type is email and this field is empty"
        },
        "sendToCustomer": {
          "type": "boolean",
          "default": true,
          "description": "Equals"
        },
        "sendType": {
          "type": "string",
          "enum": [
            "EMAIL",
            "EHF",
            "EFAKTURA",
            "AVTALEGIRO",
            "VIPPS",
            "PAPER",
            "MANUAL",
            "DIRECT",
            "AUTOINVOICE_EHF_OUTBOUND",
            "AUTOINVOICE_EHF_INCOMING",
            "PEPPOL_EHF_INCOMING"
          ],
          "description": "Equals"
        }
      },
      "required": [
        "id",
        "date"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "invoice_create_reminder_create_reminder",
    "description": "Create invoice reminder and sends it by the given dispatch type. Supports the reminder types SOFT_REMINDER, REMINDER and NOTICE_OF_DEBT_COLLECTION....",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "type": {
          "type": "string",
          "enum": [
            "SOFT_REMINDER",
            "REMINDER",
            "NOTICE_OF_DEBT_COLLECTION",
            "DEBT_COLLECTION"
          ],
          "description": "type"
        },
        "date": {
          "type": "string",
          "description": "yyyy-MM-dd. Defaults to today."
        },
        "includeCharge": {
          "type": "boolean",
          "default": false,
          "description": "Equals"
        },
        "includeInterest": {
          "type": "boolean",
          "default": false,
          "description": "Equals"
        },
        "dispatchType": {
          "type": "string",
          "enum": [
            "NETS_PRINT",
            "EMAIL",
            "OWN_PRINTER",
            "SFTP",
            "API",
            "SMS"
          ],
          "description": "dispatchType"
        },
        "dispatchTypes": {
          "type": "string",
          "description": "List of dispatch types (comma separated enum values)"
        },
        "smsNumber": {
          "type": "string",
          "description": "SMS number (must be a valid Norwegian telephone number)"
        },
        "email": {
          "type": "string",
          "description": "Email address to send the reminder to. (Defaults to to the same email list as the invoice if not provided)"
        },
        "address": {
          "type": "string",
          "description": "Address to send the reminder to. (Defaults to the customer address if not provided)"
        },
        "postalCode": {
          "type": "string",
          "description": "Postal code to send the reminder to (Defaults to the customer postal code if not provided)"
        },
        "city": {
          "type": "string",
          "description": "City to send the reminder to (Defaults to the customer city if not provided)"
        }
      },
      "required": [
        "id",
        "type",
        "date"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "invoice_get",
    "description": "Get invoice by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "invoice_pdf_download_pdf",
    "description": "Get invoice document by invoice ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "invoiceId": {
          "type": "integer",
          "format": "int64",
          "description": "Invoice ID from which PDF is downloaded."
        },
        "download": {
          "type": "boolean",
          "default": true,
          "description": "Equals"
        }
      },
      "required": [
        "invoiceId"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "invoice_payment_payment",
    "description": "Update invoice. The invoice is updated with payment information. The amount is in the invoice’s currency.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Invoice id"
        },
        "paymentDate": {
          "type": "string",
          "description": "Payment date"
        },
        "paymentTypeId": {
          "type": "integer",
          "format": "int64",
          "description": "PaymentType id"
        },
        "paidAmount": {
          "type": "number",
          "description": "Amount paid by the customer in the currency determined by the account of the paymentType"
        },
        "paidAmountCurrency": {
          "type": "number",
          "description": "Amount paid by customer in the invoice currency. Optional, but required for invoices in alternate currencies."
        }
      },
      "required": [
        "id",
        "paymentDate",
        "paymentTypeId",
        "paidAmount"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "invoice_search",
    "description": "Find invoices corresponding with sent data. Includes charged outgoing invoices only.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "List of IDs"
        },
        "invoiceDateFrom": {
          "type": "string",
          "description": "From and including"
        },
        "invoiceDateTo": {
          "type": "string",
          "description": "To and excluding"
        },
        "invoiceNumber": {
          "type": "string",
          "description": "Equals"
        },
        "kid": {
          "type": "string",
          "description": "Equals"
        },
        "voucherId": {
          "type": "string",
          "description": "List of IDs"
        },
        "customerId": {
          "type": "string",
          "description": "Equals"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "invoiceDateFrom",
        "invoiceDateTo"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "invoice_post",
    "description": "Create invoice. Related Order and OrderLines can be created first, or included as new objects inside the Invoice.",
    "input_schema": {
      "type": "object",
      "properties": {
        "sendToCustomer": {
          "type": "boolean",
          "default": true,
          "description": "Equals"
        },
        "paymentTypeId": {
          "type": "integer",
          "format": "int32",
          "description": "Payment type to register prepayment of the invoice. paymentTypeId and paidAmount are optional, but both must be provided if the invoice has already been paid."
        },
        "paidAmount": {
          "type": "number",
          "description": "Paid amount to register prepayment of the invoice, in invoice currency. paymentTypeId and paidAmount are optional, but both must be provided if the invoice has already been paid."
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "invoice_list_post_list",
    "description": "[BETA] Create multiple invoices. Max 100 at a time.",
    "input_schema": {
      "type": "object",
      "properties": {
        "sendToCustomer": {
          "type": "boolean",
          "default": true,
          "description": "Equals"
        },
        "fields": {
          "type": "string",
          "default": "*",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "invoice_send_send",
    "description": "Send invoice by ID and sendType. Optionally override email recipient.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "sendType": {
          "type": "string",
          "enum": [
            "EMAIL",
            "EHF",
            "AVTALEGIRO",
            "EFAKTURA",
            "VIPPS",
            "PAPER",
            "MANUAL"
          ],
          "description": "SendType"
        },
        "overrideEmailAddress": {
          "type": "string",
          "description": "Will override email address if sendType = EMAIL"
        }
      },
      "required": [
        "id",
        "sendType"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "ledger_account_get",
    "description": "Get account by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "ledger_account_put",
    "description": "Update account.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "ledger_account_delete",
    "description": "Delete account.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "ledger_account_list_put_list",
    "description": "Update multiple accounts.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "ledger_account_list_post_list",
    "description": "Create several accounts.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "ledger_account_list_delete_by_ids",
    "description": "Delete multiple accounts.",
    "input_schema": {
      "type": "object",
      "properties": {
        "ids": {
          "type": "string",
          "description": "ID of the elements"
        }
      },
      "required": [
        "ids"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "ledger_account_search",
    "description": "Find accounts corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "List of IDs"
        },
        "number": {
          "type": "string",
          "description": "List of IDs"
        },
        "isBankAccount": {
          "type": "boolean",
          "description": "Equals"
        },
        "isInactive": {
          "type": "boolean",
          "description": "Equals"
        },
        "isApplicableForSupplierInvoice": {
          "type": "boolean",
          "description": "Equals"
        },
        "ledgerType": {
          "type": "string",
          "enum": [
            "GENERAL",
            "CUSTOMER",
            "VENDOR",
            "EMPLOYEE",
            "ASSET"
          ],
          "description": "Ledger type"
        },
        "isBalanceAccount": {
          "type": "boolean",
          "description": "Balance account"
        },
        "saftCode": {
          "type": "string",
          "description": "SAF-T code"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "ledger_account_post",
    "description": "Create a new account.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "ledger_posting_close_postings_close_postings",
    "description": "Close postings.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "ledger_posting_get",
    "description": "Find postings by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "ledger_posting_open_post_open_post",
    "description": "Find open posts corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "date": {
          "type": "string",
          "description": "Invoice date. Format is yyyy-MM-dd (to and excl.)."
        },
        "accountId": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID for filtering"
        },
        "supplierId": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID for filtering"
        },
        "customerId": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID for filtering"
        },
        "employeeId": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID for filtering"
        },
        "departmentId": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID for filtering"
        },
        "projectId": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID for filtering"
        },
        "productId": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID for filtering"
        },
        "accountNumberFrom": {
          "type": "integer",
          "format": "int32",
          "description": "Element ID for filtering"
        },
        "accountNumberTo": {
          "type": "integer",
          "format": "int32",
          "description": "Element ID for filtering"
        },
        "accountingDimensionValue1Id": {
          "type": "integer",
          "format": "int64",
          "description": "Id of first free accounting dimension."
        },
        "accountingDimensionValue2Id": {
          "type": "integer",
          "format": "int64",
          "description": "Id of second free accounting dimension."
        },
        "accountingDimensionValue3Id": {
          "type": "integer",
          "format": "int64",
          "description": "Id of third free accounting dimension."
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "date"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "ledger_posting_search",
    "description": "Find postings corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "dateFrom": {
          "type": "string",
          "description": "Format is yyyy-MM-dd (from and incl.)."
        },
        "dateTo": {
          "type": "string",
          "description": "Format is yyyy-MM-dd (to and excl.)."
        },
        "openPostings": {
          "type": "string",
          "description": "Deprecated"
        },
        "accountId": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID for filtering"
        },
        "supplierId": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID for filtering"
        },
        "customerId": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID for filtering"
        },
        "employeeId": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID for filtering"
        },
        "departmentId": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID for filtering"
        },
        "projectId": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID for filtering"
        },
        "productId": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID for filtering"
        },
        "accountNumberFrom": {
          "type": "integer",
          "format": "int32",
          "description": "Element ID for filtering"
        },
        "accountNumberTo": {
          "type": "integer",
          "format": "int32",
          "description": "Element ID for filtering"
        },
        "type": {
          "type": "string",
          "enum": [
            "INCOMING_PAYMENT",
            "INCOMING_PAYMENT_OPPOSITE",
            "INCOMING_INVOICE_CUSTOMER_POSTING",
            "INVOICE_EXPENSE",
            "OUTGOING_INVOICE_CUSTOMER_POSTING",
            "WAGE"
          ],
          "description": "Element ID for filtering"
        },
        "accountingDimensionValue1Id": {
          "type": "integer",
          "format": "int64",
          "description": "Id of first free accounting dimension."
        },
        "accountingDimensionValue2Id": {
          "type": "integer",
          "format": "int64",
          "description": "Id of second free accounting dimension."
        },
        "accountingDimensionValue3Id": {
          "type": "integer",
          "format": "int64",
          "description": "Id of third free accounting dimension."
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "dateFrom",
        "dateTo"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "ledger_vat_type_create_relative_vat_type_create_relative_vat_type",
    "description": "Create a new relative VAT Type. These are used if the company has 'forholdsmessig fradrag for inngående MVA'.",
    "input_schema": {
      "type": "object",
      "properties": {
        "name": {
          "type": "string",
          "description": "VAT type name, max 8 characters."
        },
        "vatTypeId": {
          "type": "integer",
          "format": "int64",
          "description": "VAT type ID. The relative VAT type will behave like this VAT type, except for the basis for calculating the VAT deduction, which is decided by the basis percentage."
        },
        "percentage": {
          "type": "number",
          "description": "Basis percentage. This percentage will be multiplied with the transaction amount to find the amount that will be the basis for calculating the deduction amount."
        }
      },
      "required": [
        "name",
        "vatTypeId",
        "percentage"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "ledger_vat_type_get",
    "description": "Get vat type by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "ledger_vat_type_search",
    "description": "Find vat types corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "List of IDs"
        },
        "number": {
          "type": "string",
          "description": "List of IDs"
        },
        "typeOfVat": {
          "type": "string",
          "enum": [
            "OUTGOING",
            "INCOMING",
            "INCOMING_INVOICE",
            "PROJECT",
            "LEDGER"
          ],
          "description": "Type of VAT"
        },
        "vatDate": {
          "type": "string",
          "description": "yyyy-MM-dd. Defaults to today. Note that this is only used in combination with typeOfVat-parameter. Only valid vatTypes on the given date are returned."
        },
        "shouldIncludeSpecificationTypes": {
          "type": "boolean",
          "description": "Equals"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "ledger_voucher_get",
    "description": "Get voucher by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "ledger_voucher_put",
    "description": "Update voucher. Postings with guiRow==0 will be deleted and regenerated.",
    "input_schema": {
      "type": "object",
      "properties": {
        "sendToLedger": {
          "type": "boolean",
          "default": true,
          "description": "Should the voucher be sent to ledger? Requires the \"Advanced Voucher\" permission."
        },
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "ledger_voucher_delete",
    "description": "Delete voucher by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "ledger_voucher_attachment_upload_attachment",
    "description": "Upload attachment to voucher. If the voucher already has an attachment the content will be appended to the existing attachment as new PDF page(s). ...",
    "input_schema": {
      "type": "object",
      "properties": {
        "voucherId": {
          "type": "integer",
          "format": "int64",
          "description": "Voucher ID to upload attachment to."
        }
      },
      "required": [
        "voucherId"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "ledger_voucher_attachment_delete_attachment",
    "description": "Delete attachment.",
    "input_schema": {
      "type": "object",
      "properties": {
        "voucherId": {
          "type": "integer",
          "format": "int64",
          "description": "ID of voucher containing the attachment to delete."
        },
        "version": {
          "minimum": 0,
          "type": "integer",
          "format": "int32",
          "description": "Version of voucher containing the attachment to delete."
        },
        "sendToInbox": {
          "type": "boolean",
          "default": false,
          "description": "Should the attachment be sent to inbox rather than deleted?"
        },
        "split": {
          "type": "boolean",
          "default": false,
          "description": "If sendToInbox is true, should the attachment be split into one voucher per page?"
        }
      },
      "required": [
        "voucherId"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "ledger_voucher_pdf_download_pdf",
    "description": "Get PDF representation of voucher by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "voucherId": {
          "type": "integer",
          "format": "int64",
          "description": "Voucher ID from which PDF is downloaded."
        }
      },
      "required": [
        "voucherId"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "ledger_voucher_external_voucher_number_external_voucher_number",
    "description": "Find vouchers based on the external voucher number.",
    "input_schema": {
      "type": "object",
      "properties": {
        "externalVoucherNumber": {
          "type": "string",
          "description": "The external voucher number, when voucher is created from import."
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "ledger_voucher_import_document_import_document",
    "description": "Upload a document to create one or more vouchers. Valid document formats are PDF, PNG, JPEG and TIFF. EHF/XML is possible with agreement with Tripl...",
    "input_schema": {
      "type": "object",
      "properties": {
        "split": {
          "type": "boolean",
          "default": false,
          "description": "If the document consists of several pages, should the document be split into one voucher per page?"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "ledger_voucher_import_gbat10_import_gbat10",
    "description": "Import GBAT10. Send as multipart form.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "ledger_voucher_non_posted_non_posted",
    "description": "Find non-posted vouchers.",
    "input_schema": {
      "type": "object",
      "properties": {
        "dateFrom": {
          "type": "string",
          "description": "From and including"
        },
        "dateTo": {
          "type": "string",
          "description": "To and excluding"
        },
        "includeNonApproved": {
          "type": "boolean",
          "default": false,
          "description": "Include non-approved vouchers in the result."
        },
        "changedSince": {
          "type": "string",
          "description": "Only return elements that have changed since this date and time"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "includeNonApproved"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "ledger_voucher_options_options",
    "description": "Returns a data structure containing meta information about operations that are available for this voucher. Currently only implemented for DELETE: I...",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "ledger_voucher_search",
    "description": "Find vouchers corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "List of IDs"
        },
        "number": {
          "type": "string",
          "description": "List of IDs"
        },
        "numberFrom": {
          "type": "integer",
          "format": "int32",
          "description": "From and including"
        },
        "numberTo": {
          "type": "integer",
          "format": "int32",
          "description": "To and excluding"
        },
        "typeId": {
          "type": "string",
          "description": "List of IDs"
        },
        "dateFrom": {
          "type": "string",
          "description": "From and including"
        },
        "dateTo": {
          "type": "string",
          "description": "To and excluding"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "dateFrom",
        "dateTo"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "ledger_voucher_post",
    "description": "Add new voucher. IMPORTANT: Also creates postings. Only the gross amounts will be used. Amounts should be rounded to 2 decimals.",
    "input_schema": {
      "type": "object",
      "properties": {
        "sendToLedger": {
          "type": "boolean",
          "default": true,
          "description": "Should the voucher be sent to ledger? Requires the \"Advanced Voucher\" permission."
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "ledger_voucher_list_put_list",
    "description": "Update multiple vouchers. Postings with guiRow==0 will be deleted and regenerated.",
    "input_schema": {
      "type": "object",
      "properties": {
        "sendToLedger": {
          "type": "boolean",
          "default": true,
          "description": "Should the voucher be sent to ledger? Requires the \"Advanced Voucher\" permission."
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "ledger_voucher_reverse_reverse",
    "description": "Reverses the voucher, and returns the reversed voucher. Supports reversing most voucher types, except salary transactions.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "ID of voucher that should be reversed."
        },
        "date": {
          "type": "string",
          "description": "Reverse voucher date"
        }
      },
      "required": [
        "id",
        "date"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "ledger_voucher_send_to_inbox_send_to_inbox",
    "description": "Send voucher to inbox.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "ID of voucher that should be sent to inbox."
        },
        "version": {
          "minimum": 0,
          "type": "integer",
          "format": "int32",
          "description": "Version of voucher that should be sent to inbox."
        },
        "comment": {
          "type": "string",
          "description": "Description of why the voucher was rejected. This parameter is only used if the approval feature is enabled."
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "ledger_voucher_send_to_ledger_send_to_ledger",
    "description": "Send voucher to ledger.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "ID of voucher that should be sent to ledger."
        },
        "version": {
          "minimum": 0,
          "type": "integer",
          "format": "int32",
          "description": "Version of voucher that should be sent to ledger."
        },
        "number": {
          "minimum": 0,
          "type": "integer",
          "format": "int32",
          "default": 0,
          "description": "Voucher number to use. If omitted or 0 the system will assign the number."
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "ledger_voucher_pdf_upload_pdf",
    "description": "[DEPRECATED] Use POST ledger/voucher/{voucherId}/attachment instead.",
    "input_schema": {
      "type": "object",
      "properties": {
        "voucherId": {
          "type": "integer",
          "format": "int64",
          "description": "Voucher ID to upload PDF to."
        },
        "fileName": {
          "type": "string",
          "description": "File name to store the pdf under. Will not be the same as the filename on the file returned."
        }
      },
      "required": [
        "voucherId",
        "fileName"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "ledger_voucher_voucher_reception_voucher_reception",
    "description": "Find vouchers in voucher reception.",
    "input_schema": {
      "type": "object",
      "properties": {
        "dateFrom": {
          "type": "string",
          "description": "From and including"
        },
        "dateTo": {
          "type": "string",
          "description": "To and excluding"
        },
        "searchText": {
          "type": "string",
          "description": "Search"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "municipality_query_query",
    "description": "[BETA] Wildcard search.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "List of IDs"
        },
        "query": {
          "type": "string",
          "description": "Containing"
        },
        "fields": {
          "type": "string",
          "default": "id, displayName",
          "description": "Fields filter pattern"
        },
        "count": {
          "type": "integer",
          "format": "int32",
          "default": 25,
          "description": "Number of elements to return"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "municipality_search",
    "description": "Get municipalities.",
    "input_schema": {
      "type": "object",
      "properties": {
        "includePayrollTaxZones": {
          "type": "boolean",
          "default": true,
          "description": "Equals"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "order_approve_subscription_invoice_approve_subscription_invoice",
    "description": "To create a subscription invoice, first create a order with the subscription enabled, then approve it with this method. This approves the order for...",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "ID of order to approve for subscription invoicing."
        },
        "invoiceDate": {
          "type": "string",
          "description": "The approval date for the subscription."
        }
      },
      "required": [
        "id",
        "invoiceDate"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "order_attach_attach",
    "description": "Attach document to specified order ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "order_get",
    "description": "Get order by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "order_put",
    "description": "Update order.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "updateLinesAndGroups": {
          "type": "boolean",
          "default": false,
          "description": "Should order lines and order groups be saved and not included lines/groups be removed? Only applies if non null list of order lines or order groups is set."
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "order_delete",
    "description": "Delete order.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "order_packing_note_pdf_download_packing_note_pdf",
    "description": "Get PDF representation of packing note by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "orderId": {
          "type": "integer",
          "format": "int32",
          "description": "Order ID from which PDF is downloaded."
        },
        "type": {
          "type": "string",
          "enum": [
            "ALL_ORDER_LINES",
            "STOCK_ITEMS_ONLY"
          ],
          "default": "ALL_ORDER_LINES",
          "description": "Type of packing note to download."
        },
        "download": {
          "type": "boolean",
          "default": true,
          "description": "Equals"
        }
      },
      "required": [
        "orderId"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "order_order_confirmation_pdf_download_pdf",
    "description": "Get PDF representation of order by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "orderId": {
          "type": "integer",
          "format": "int32",
          "description": "Order ID from which PDF is downloaded."
        },
        "download": {
          "type": "boolean",
          "default": true,
          "description": "Equals"
        }
      },
      "required": [
        "orderId"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "order_invoice_invoice",
    "description": "Create new invoice or subscription invoice from order.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "ID of order to invoice."
        },
        "invoiceDate": {
          "type": "string",
          "description": "The invoice date"
        },
        "sendToCustomer": {
          "type": "boolean",
          "default": true,
          "description": "Send invoice to customer"
        },
        "sendType": {
          "type": "string",
          "enum": [
            "EMAIL",
            "EHF",
            "AVTALEGIRO",
            "EFAKTURA",
            "VIPPS",
            "PAPER",
            "MANUAL"
          ],
          "description": "Send type used for sending the invoice"
        },
        "paymentTypeId": {
          "type": "integer",
          "format": "int64",
          "description": "Payment type to register prepayment of the invoice. paymentTypeId and paidAmount are optional, but both must be provided if the invoice has already been paid. The payment type must be related to an account with the same currency as the invoice."
        },
        "paidAmount": {
          "type": "number",
          "description": "Paid amount to register prepayment of the invoice, in invoice currency. paymentTypeId and paidAmount are optional, but both must be provided if the invoice has already been paid. This amount is in the invoice currency."
        },
        "paidAmountAccountCurrency": {
          "type": "number",
          "description": "Amount paid in payment type currency"
        },
        "paymentTypeIdRestAmount": {
          "type": "integer",
          "format": "int64",
          "description": "Payment type of rest amount. It is possible to have two prepaid payments when invoicing. If paymentTypeIdRestAmount > 0, this second payment will be calculated as invoice amount - paidAmount"
        },
        "paidAmountAccountCurrencyRest": {
          "type": "number",
          "description": "Amount rest in payment type currency"
        },
        "createOnAccount": {
          "type": "string",
          "enum": [
            "NONE",
            "WITH_VAT",
            "WITHOUT_VAT"
          ],
          "description": "Create on account(a konto)"
        },
        "amountOnAccount": {
          "type": "number",
          "default": 0,
          "description": "Amount on account"
        },
        "onAccountComment": {
          "type": "string",
          "default": "",
          "description": "On account comment"
        },
        "createBackorder": {
          "type": "boolean",
          "default": false,
          "description": "Create a backorder for this order, available only for pilot users"
        },
        "invoiceIdIfIsCreditNote": {
          "type": "integer",
          "format": "int64",
          "default": 0,
          "description": "Id of the invoice a credit note refers to"
        },
        "overrideEmailAddress": {
          "type": "string",
          "description": "Will override email address if sendType = EMAIL"
        }
      },
      "required": [
        "id",
        "invoiceDate"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "order_invoice_multiple_orders_invoice_multiple_orders",
    "description": "[BETA] Charges a single customer invoice from multiple orders. The orders must be to the same customer, currency, due date, receiver email, attn. a...",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "List of Order IDs - to the same customer, separated by comma."
        },
        "invoiceDate": {
          "type": "string",
          "description": "The invoice date"
        },
        "sendToCustomer": {
          "type": "boolean",
          "default": true,
          "description": "Send invoice to customer"
        },
        "createBackorders": {
          "type": "boolean",
          "default": false,
          "description": "Create a backorder for all any orders that delivers less than ordered amount"
        }
      },
      "required": [
        "id",
        "invoiceDate"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "order_search",
    "description": "Find orders corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "List of IDs"
        },
        "number": {
          "type": "string",
          "description": "Equals"
        },
        "customerId": {
          "type": "string",
          "description": "List of IDs"
        },
        "orderDateFrom": {
          "type": "string",
          "description": "From and including"
        },
        "orderDateTo": {
          "type": "string",
          "description": "To and excluding"
        },
        "deliveryComment": {
          "type": "string",
          "description": "Containing"
        },
        "isClosed": {
          "type": "boolean",
          "description": "Equals"
        },
        "isSubscription": {
          "type": "boolean",
          "description": "Equals"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "orderDateFrom",
        "orderDateTo"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "order_post",
    "description": "Create order.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "order_send_invoice_preview_post_invoice_preview",
    "description": "Send Invoice Preview to customer by email.",
    "input_schema": {
      "type": "object",
      "properties": {
        "orderId": {
          "type": "integer",
          "format": "int64",
          "description": "orderId"
        },
        "email": {
          "type": "string",
          "description": "email"
        },
        "message": {
          "type": "string",
          "description": "message"
        },
        "saveAsDefault": {
          "type": "boolean",
          "description": "saveAsDefault"
        }
      },
      "required": [
        "orderId"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "order_list_post_list",
    "description": "[BETA] Create multiple Orders with OrderLines. Max 100 at a time.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "order_send_order_confirmation_post_order_confirmation",
    "description": "Send Order Confirmation to customer by email.",
    "input_schema": {
      "type": "object",
      "properties": {
        "orderId": {
          "type": "integer",
          "format": "int64",
          "description": "orderId"
        },
        "email": {
          "type": "string",
          "description": "email"
        },
        "message": {
          "type": "string",
          "description": "message"
        },
        "saveAsDefault": {
          "type": "boolean",
          "description": "saveAsDefault"
        }
      },
      "required": [
        "orderId"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "order_send_packing_note_post_packing_note",
    "description": "Send Packing Note to customer by email.",
    "input_schema": {
      "type": "object",
      "properties": {
        "orderId": {
          "type": "integer",
          "format": "int64",
          "description": "orderId"
        },
        "email": {
          "type": "string",
          "description": "email"
        },
        "message": {
          "type": "string",
          "description": "message"
        },
        "saveAsDefault": {
          "type": "boolean",
          "description": "saveAsDefault"
        },
        "type": {
          "type": "string",
          "enum": [
            "ALL_ORDER_LINES",
            "STOCK_ITEMS_ONLY"
          ],
          "default": "ALL_ORDER_LINES",
          "description": "Type of packing note to send."
        }
      },
      "required": [
        "orderId"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "order_un_approve_subscription_invoice_un_approve_subscription_invoice",
    "description": "Unapproves the order for subscription invoicing.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "ID of order to unapprove for subscription invoicing."
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "order_orderline_get",
    "description": "Get order line by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "order_orderline_put",
    "description": "[BETA] Put order line",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "order_orderline_delete",
    "description": "[BETA] Delete order line by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "order_orderline_list_post_list",
    "description": "Create multiple order lines.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "order_orderline_order_line_template_order_line_template",
    "description": "[BETA] Get order line template from order and product",
    "input_schema": {
      "type": "object",
      "properties": {
        "orderId": {
          "type": "integer",
          "format": "int64",
          "description": "Equals"
        },
        "productId": {
          "type": "integer",
          "format": "int64",
          "description": "Equals"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "orderId",
        "productId"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "order_orderline_pick_line_pick_line",
    "description": "[BETA] Pick order line. This is only available for customers who have Logistics and who activated the available inventory functionality.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Order line id"
        },
        "inventoryId": {
          "type": "integer",
          "format": "int64",
          "description": "Optional inventory id. If no inventory is sent, default inventory will be used."
        },
        "inventoryLocationId": {
          "type": "integer",
          "format": "int64",
          "description": "Optional inventory location id"
        },
        "pickDate": {
          "type": "string",
          "description": "Optional pick date. If not sent, current date will be used."
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "order_orderline_post",
    "description": "Create order line. When creating several order lines, use /list for better performance.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "order_orderline_unpick_line_unpick_line",
    "description": "[BETA] Unpick order line.This is only available for customers who have Logistics and who activated the available inventory functionality.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Order line id"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "product_get",
    "description": "Get product by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "product_put",
    "description": "Update product.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "product_delete",
    "description": "Delete product.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "product_image_upload_image",
    "description": "Upload image to product. Existing image on product will be replaced if exists",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Product ID to upload image to."
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "product_image_delete_image",
    "description": "Delete image.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "ID of Product containing the image to delete."
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "product_list_put_list",
    "description": "Update a list of products.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "product_list_post_list",
    "description": "Add multiple products.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "product_search",
    "description": "Find products corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "number": {
          "type": "string",
          "description": "DEPRECATED. List of product numbers (Integer only)"
        },
        "ids": {
          "type": "string",
          "description": "List of IDs"
        },
        "productNumber": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "List of valid product numbers"
        },
        "name": {
          "type": "string",
          "description": "Containing"
        },
        "ean": {
          "type": "string",
          "description": "Equals"
        },
        "isInactive": {
          "type": "boolean",
          "description": "Equals"
        },
        "isStockItem": {
          "type": "boolean",
          "description": "Equals"
        },
        "isSupplierProduct": {
          "type": "boolean",
          "description": "Equals"
        },
        "supplierId": {
          "type": "string",
          "description": "Equals"
        },
        "currencyId": {
          "type": "string",
          "description": "Equals"
        },
        "vatTypeId": {
          "type": "string",
          "description": "Equals"
        },
        "productUnitId": {
          "type": "string",
          "description": "Equals"
        },
        "departmentId": {
          "type": "string",
          "description": "Equals"
        },
        "accountId": {
          "type": "string",
          "description": "Equals"
        },
        "costExcludingVatCurrencyFrom": {
          "type": "number",
          "description": "From and including"
        },
        "costExcludingVatCurrencyTo": {
          "type": "number",
          "description": "To and excluding"
        },
        "priceExcludingVatCurrencyFrom": {
          "type": "number",
          "description": "From and including"
        },
        "priceExcludingVatCurrencyTo": {
          "type": "number",
          "description": "To and excluding"
        },
        "priceIncludingVatCurrencyFrom": {
          "type": "number",
          "description": "From and including"
        },
        "priceIncludingVatCurrencyTo": {
          "type": "number",
          "description": "To and excluding"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "product_post",
    "description": "Create new product.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "product_unit_get",
    "description": "Get product unit by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "product_unit_put",
    "description": "Update product unit.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "product_unit_delete",
    "description": "Delete product unit by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "product_unit_search",
    "description": "Find product units corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "List of IDs"
        },
        "name": {
          "type": "string",
          "description": "Names"
        },
        "nameShort": {
          "type": "string",
          "description": "Short names"
        },
        "commonCode": {
          "type": "string",
          "description": "Common codes"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "product_unit_post",
    "description": "Create new product unit.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "product_unit_list_put_list",
    "description": "Update list of product units.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "product_unit_list_post_list",
    "description": "Create multiple product units.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "product_unit_query_query",
    "description": "Wildcard search.",
    "input_schema": {
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "Containing"
        },
        "count": {
          "type": "integer",
          "format": "int32",
          "default": 25,
          "description": "Number of elements to return"
        },
        "fields": {
          "type": "string",
          "default": "id, name",
          "description": "Fields filter pattern"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "project_get",
    "description": "Find project by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "project_put",
    "description": "[BETA] Update project.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "project_delete",
    "description": "[BETA] Delete project.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "project_list_put_list",
    "description": "[BETA] Update multiple projects.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "project_list_post_list",
    "description": "[BETA] Register new projects. Multiple projects for different users can be sent in the same request.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "project_list_delete_by_ids",
    "description": "[BETA] Delete projects.",
    "input_schema": {
      "type": "object",
      "properties": {
        "ids": {
          "type": "string",
          "description": "ID of the elements"
        }
      },
      "required": [
        "ids"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "project_search",
    "description": "Find projects corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "List of IDs"
        },
        "name": {
          "type": "string",
          "description": "Containing"
        },
        "number": {
          "type": "string",
          "description": "Equals"
        },
        "isOffer": {
          "type": "boolean",
          "description": "Equals"
        },
        "projectManagerId": {
          "type": "string",
          "description": "List of IDs"
        },
        "customerAccountManagerId": {
          "type": "string",
          "description": "List of IDs"
        },
        "employeeInProjectId": {
          "type": "string",
          "description": "List of IDs"
        },
        "departmentId": {
          "type": "string",
          "description": "List of IDs"
        },
        "startDateFrom": {
          "type": "string",
          "description": "From and including"
        },
        "startDateTo": {
          "type": "string",
          "description": "To and excluding"
        },
        "endDateFrom": {
          "type": "string",
          "description": "From and including"
        },
        "endDateTo": {
          "type": "string",
          "description": "To and excluding"
        },
        "isClosed": {
          "type": "boolean",
          "description": "Equals"
        },
        "isFixedPrice": {
          "type": "boolean",
          "description": "Equals"
        },
        "customerId": {
          "type": "string",
          "description": "Equals"
        },
        "externalAccountsNumber": {
          "type": "string",
          "description": "Containing"
        },
        "includeRecentlyClosed": {
          "type": "boolean",
          "default": false,
          "description": "If isClosed is false, include projects that have been closed within the last 3 months. Equals"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "project_post",
    "description": "Add new project.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "project_delete_list",
    "description": "[BETA] Delete multiple projects.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "project_number_get_by_number",
    "description": "Find project by number.",
    "input_schema": {
      "type": "object",
      "properties": {
        "number": {
          "type": "string",
          "description": "Number of the project"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "number"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "project_for_time_sheet_get_for_time_sheet",
    "description": "Find projects applicable for time sheet registration on a specific day.",
    "input_schema": {
      "type": "object",
      "properties": {
        "includeProjectOffers": {
          "type": "boolean",
          "default": false,
          "description": "Equals"
        },
        "employeeId": {
          "type": "integer",
          "format": "int64",
          "description": "Employee ID. Defaults to ID of token owner."
        },
        "date": {
          "type": "string",
          "description": "yyyy-MM-dd. Defaults to today."
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "project_import_import_project_statement",
    "description": "Upload project import file.",
    "input_schema": {
      "type": "object",
      "properties": {
        "fileFormat": {
          "type": "string",
          "enum": [
            "XLS",
            "CSV"
          ],
          "description": "File format"
        },
        "encoding": {
          "type": "string",
          "description": "Encoding"
        },
        "delimiter": {
          "type": "string",
          "description": "Delimiter"
        },
        "ignoreFirstRow": {
          "type": "boolean",
          "description": "Ignore first row"
        }
      },
      "required": [
        "fileFormat"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "project_orderline_get",
    "description": "[BETA] Get order line by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "project_orderline_put",
    "description": "[BETA] Update project orderline.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "project_orderline_delete",
    "description": "Delete order line by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "project_orderline_list_post_list",
    "description": "[BETA] Create multiple order lines.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "project_orderline_order_line_template_order_line_template",
    "description": "[BETA] Get order line template from project and product",
    "input_schema": {
      "type": "object",
      "properties": {
        "projectId": {
          "type": "integer",
          "format": "int64",
          "description": "Equals"
        },
        "productId": {
          "type": "integer",
          "format": "int64",
          "description": "Equals"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "projectId",
        "productId"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "project_orderline_search",
    "description": "[BETA] Find all order lines for project.",
    "input_schema": {
      "type": "object",
      "properties": {
        "projectId": {
          "type": "integer",
          "format": "int64",
          "description": "Equals"
        },
        "isBudget": {
          "type": "boolean",
          "description": "Equals"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "projectId"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "project_orderline_post",
    "description": "[BETA] Create order line. When creating several order lines, use /list for better performance.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "project_orderline_query_query",
    "description": "[BETA] Wildcard search.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "List of IDs"
        },
        "projectId": {
          "type": "integer",
          "format": "int64",
          "description": "Equals"
        },
        "query": {
          "type": "string",
          "description": "Containing"
        },
        "isBudget": {
          "type": "boolean",
          "description": "Equals"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "project_participant_list_post_list",
    "description": "[BETA] Add new project participant. Multiple project participants can be sent in the same request.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "project_participant_list_delete_by_ids",
    "description": "[BETA] Delete project participants.",
    "input_schema": {
      "type": "object",
      "properties": {
        "ids": {
          "type": "string",
          "description": "ID of the elements"
        }
      },
      "required": [
        "ids"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "project_participant_get",
    "description": "[BETA] Find project participant by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "project_participant_put",
    "description": "[BETA] Update project participant.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "project_participant_post",
    "description": "[BETA] Add new project participant.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "project_hourly_rates_get",
    "description": "Find project hourly rate by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "project_hourly_rates_put",
    "description": "Update a project hourly rate.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "project_hourly_rates_delete",
    "description": "Delete Project Hourly Rate ",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "project_hourly_rates_list_put_list",
    "description": "Update multiple project hourly rates.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "project_hourly_rates_list_post_list",
    "description": "Create multiple project hourly rates.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "project_hourly_rates_list_delete_by_ids",
    "description": "Delete project hourly rates.",
    "input_schema": {
      "type": "object",
      "properties": {
        "ids": {
          "type": "string",
          "description": "ID of the elements"
        }
      },
      "required": [
        "ids"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "project_hourly_rates_delete_by_project_ids_delete_by_project_ids",
    "description": "Delete project hourly rates by project id.",
    "input_schema": {
      "type": "object",
      "properties": {
        "ids": {
          "type": "string",
          "description": "ID of the elements"
        },
        "date": {
          "type": "string",
          "description": "yyyy-MM-dd. Defaults to today."
        }
      },
      "required": [
        "ids",
        "date"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "project_hourly_rates_search",
    "description": "Find project hourly rates corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "List of IDs"
        },
        "projectId": {
          "type": "string",
          "description": "List of IDs"
        },
        "type": {
          "type": "string",
          "enum": [
            "TYPE_PREDEFINED_HOURLY_RATES",
            "TYPE_PROJECT_SPECIFIC_HOURLY_RATES",
            "TYPE_FIXED_HOURLY_RATE"
          ],
          "description": "Equals"
        },
        "startDateFrom": {
          "type": "string",
          "description": "From and including"
        },
        "startDateTo": {
          "type": "string",
          "description": "To and excluding"
        },
        "showInProjectOrder": {
          "type": "boolean",
          "description": "Equals"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "project_hourly_rates_post",
    "description": "Create a project hourly rate. ",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "project_hourly_rates_update_or_add_hour_rates_update_or_add_hour_rates",
    "description": "Update or add the same project hourly rate from project overview.",
    "input_schema": {
      "type": "object",
      "properties": {
        "ids": {
          "type": "string",
          "description": "ID of the elements"
        },
        "id": {
          "type": "integer",
          "format": "int64"
        },
        "version": {
          "type": "integer",
          "format": "int32"
        },
        "startDate": {
          "type": "string"
        },
        "hourlyRateModel": {
          "type": "string",
          "description": "Defines the model used for the hourly rate.",
          "enum": [
            "TYPE_PREDEFINED_HOURLY_RATES",
            "TYPE_PROJECT_SPECIFIC_HOURLY_RATES",
            "TYPE_FIXED_HOURLY_RATE"
          ]
        },
        "projectSpecificRates": {
          "type": "array",
          "description": "Project specific rates if hourlyRateModel is TYPE_PROJECT_SPECIFIC_HOURLY_RATES. ",
          "items": {
            "type": "object",
            "properties": {
              "id": {
                "type": "integer"
              },
              "version": {
                "type": "integer"
              },
              "changes": {
                "type": "array"
              },
              "url": {
                "type": "string"
              },
              "hourlyRate": {
                "type": "number"
              },
              "hourlyCostPercentage": {
                "type": "number"
              },
              "projectHourlyRate": {
                "type": "object"
              },
              "employee": {
                "type": "object"
              },
              "activity": {
                "type": "object"
              }
            },
            "description": "Project specific rates if hourlyRateModel is TYPE_PROJECT_SPECIFIC_HOURLY_RATES. "
          }
        },
        "fixedRate": {
          "type": "number",
          "description": "Fixed Hourly rates if hourlyRateModel is TYPE_FIXED_HOURLY_RATE."
        }
      },
      "required": [
        "ids"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "project_hourly_rates_project_specific_rates_get",
    "description": "Find project specific rate by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "project_hourly_rates_project_specific_rates_put",
    "description": "Update a project specific rate.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "project_hourly_rates_project_specific_rates_delete",
    "description": "Delete project specific rate ",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "project_hourly_rates_project_specific_rates_list_put_list",
    "description": "Update multiple project specific rates.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "project_hourly_rates_project_specific_rates_list_post_list",
    "description": "Create multiple new project specific rates.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "project_hourly_rates_project_specific_rates_list_delete_by_ids",
    "description": "Delete project specific rates.",
    "input_schema": {
      "type": "object",
      "properties": {
        "ids": {
          "type": "string",
          "description": "ID of the elements"
        }
      },
      "required": [
        "ids"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "project_hourly_rates_project_specific_rates_search",
    "description": "Find project specific rates corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "List of IDs"
        },
        "projectHourlyRateId": {
          "type": "string",
          "description": "List of IDs"
        },
        "employeeId": {
          "type": "string",
          "description": "List of IDs"
        },
        "activityId": {
          "type": "string",
          "description": "List of IDs"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "project_hourly_rates_project_specific_rates_post",
    "description": "Create new project specific rate. ",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "purchase_order_get",
    "description": "Find purchase order by ID. Only available for Logistics Basic.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "purchase_order_put",
    "description": " Update purchase order. Only available for Logistics Basic.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "purchase_order_delete",
    "description": " Delete purchase order. Only available for Logistics Basic.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "purchase_order_attachment_upload_attachment",
    "description": "Upload attachment to purchase order. Only available for Logistics Basic.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Purchase Order ID to upload attachment to."
        },
        "fields": {
          "type": "string",
          "default": "*",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "purchase_order_attachment_delete_attachment",
    "description": "Delete attachment. Only available for Logistics Basic.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "ID of purchase order containing the attachment to delete."
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "purchase_order_search",
    "description": "Find purchase orders with send data. Only available for Logistics Basic.",
    "input_schema": {
      "type": "object",
      "properties": {
        "number": {
          "type": "string",
          "description": "Equals"
        },
        "deliveryDateFrom": {
          "type": "string",
          "description": "Format is yyyy-MM-dd (from and incl.)."
        },
        "deliveryDateTo": {
          "type": "string",
          "description": "Format is yyyy-MM-dd (to and incl.)."
        },
        "creationDateFrom": {
          "type": "string",
          "description": "Format is yyyy-MM-dd (from and incl.)."
        },
        "creationDateTo": {
          "type": "string",
          "description": "Format is yyyy-MM-dd (to and incl.)."
        },
        "id": {
          "type": "string",
          "description": "List of IDs"
        },
        "supplierId": {
          "type": "string",
          "description": "List of IDs"
        },
        "projectId": {
          "type": "string",
          "description": "List of IDs"
        },
        "isClosed": {
          "type": "boolean",
          "description": "Equals"
        },
        "withDeviationOnly": {
          "type": "boolean",
          "default": false,
          "description": "Equals"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "purchase_order_post",
    "description": "Creates a new purchase order. Only available for Logistics Basic.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "purchase_order_send_send",
    "description": "Send purchase order by ID and sendType. Only available for Logistics Basic.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "sendType": {
          "type": "string",
          "enum": [
            "DEFAULT",
            "EMAIL",
            "FTP"
          ],
          "default": "DEFAULT",
          "description": "Send type.DEFAULT will determine the send parameter based on the supplier type.If supplier is not wholesaler, receiverEmail from the PO will be used if it's specified.If receiverEmail empty it will take the vendor email."
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "purchase_order_send_by_email_send_by_email",
    "description": "Send purchase order by customisable email. Only available for Logistics Basic.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "purchase_order_attachment_list_upload_attachments",
    "description": "Upload multiple attachments to Purchase Order. Only available for Logistics Basic.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Purchase Order ID to upload attachment to."
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "purchase_order_orderline_get",
    "description": "Find purchase order line by ID. Only available for Logistics Basic.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "purchase_order_orderline_put",
    "description": "Updates purchase order line. Only available for Logistics Basic.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "purchase_order_orderline_delete",
    "description": "Delete purchase order line. Only available for Logistics Basic.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "purchase_order_orderline_list_put_list",
    "description": "Update a list of purchase order lines. Only available for Logistics Basic.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "purchase_order_orderline_list_post_list",
    "description": "Create list of new purchase order lines. Only available for Logistics Basic.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "purchase_order_orderline_list_delete_list",
    "description": "Delete purchase order lines by ID. Only available for Logistics Basic.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "purchase_order_orderline_post",
    "description": "Creates purchase order line. Only available for Logistics Basic.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "salary_type_get",
    "description": "Find salary type by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "salary_type_search",
    "description": "Find salary type corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "List of IDs"
        },
        "number": {
          "type": "string",
          "description": "Containing"
        },
        "name": {
          "type": "string",
          "description": "Containing"
        },
        "description": {
          "type": "string",
          "description": "Containing"
        },
        "showInTimesheet": {
          "type": "boolean",
          "description": "Equals"
        },
        "isInactive": {
          "type": "boolean",
          "description": "Equals"
        },
        "employeeIds": {
          "type": "string",
          "description": "Equals"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "supplier_get",
    "description": "Get supplier by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "supplier_put",
    "description": "Update supplier. ",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "supplier_delete",
    "description": "Delete supplier by ID",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "supplier_search",
    "description": "Find suppliers corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "List of IDs"
        },
        "supplierNumber": {
          "type": "string",
          "description": "List of IDs"
        },
        "organizationNumber": {
          "type": "string",
          "description": "Equals"
        },
        "email": {
          "type": "string",
          "description": "Equals"
        },
        "invoiceEmail": {
          "type": "string",
          "description": "Equals"
        },
        "isInactive": {
          "type": "boolean",
          "default": false,
          "description": "Equals"
        },
        "accountManagerId": {
          "type": "string",
          "description": "List of IDs"
        },
        "changedSince": {
          "type": "string",
          "description": "Only return elements that have changed since this date and time"
        },
        "isWholesaler": {
          "type": "boolean",
          "description": "Equals"
        },
        "showProducts": {
          "type": "boolean",
          "description": "Equals"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "supplier_post",
    "description": "Create supplier. Related supplier addresses may also be created.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "supplier_list_put_list",
    "description": "Update multiple suppliers. Addresses can also be updated.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "supplier_list_post_list",
    "description": "Create multiple suppliers. Related supplier addresses may also be created.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "supplier_invoice_add_payment_add_payment",
    "description": "Register payment, paymentType == 0 finds the last paymentType for this vendor.Use of this method requires setup done by Tripletex.",
    "input_schema": {
      "type": "object",
      "properties": {
        "invoiceId": {
          "type": "integer",
          "format": "int64",
          "description": "Invoice ID."
        },
        "paymentType": {
          "type": "integer",
          "format": "int32",
          "description": "paymentType"
        },
        "amount": {
          "type": "number",
          "description": "amount"
        },
        "kidOrReceiverReference": {
          "type": "string",
          "description": "kidOrReceiverReference"
        },
        "bban": {
          "type": "string",
          "description": "bban"
        },
        "paymentDate": {
          "type": "string",
          "description": "paymentDate"
        },
        "useDefaultPaymentType": {
          "type": "boolean",
          "default": false,
          "description": "Set paymentType to last type for vendor, autopay, nets or first available other type"
        },
        "partialPayment": {
          "type": "boolean",
          "default": false,
          "description": "Set to true to allow multiple payments registered."
        }
      },
      "required": [
        "invoiceId",
        "paymentType"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "supplier_invoice_add_recipient_add_recipient",
    "description": "Add recipient to supplier invoices.",
    "input_schema": {
      "type": "object",
      "properties": {
        "invoiceId": {
          "type": "integer",
          "format": "int64",
          "description": "Invoice ID."
        },
        "employeeId": {
          "type": "integer",
          "format": "int64",
          "description": "ID of the elements"
        },
        "comment": {
          "type": "string",
          "description": "comment"
        }
      },
      "required": [
        "invoiceId",
        "employeeId"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "supplier_invoice_add_recipient_add_recipient_to_many",
    "description": "Add recipient.",
    "input_schema": {
      "type": "object",
      "properties": {
        "employeeId": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "invoiceIds": {
          "type": "string",
          "description": "ID of the elements"
        },
        "comment": {
          "type": "string",
          "description": "comment"
        }
      },
      "required": [
        "employeeId"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "supplier_invoice_approve_approve",
    "description": "Approve supplier invoice.",
    "input_schema": {
      "type": "object",
      "properties": {
        "invoiceId": {
          "type": "integer",
          "format": "int64",
          "description": "ID of the elements"
        },
        "comment": {
          "type": "string",
          "description": "comment"
        }
      },
      "required": [
        "invoiceId"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "supplier_invoice_approve_approve_many",
    "description": "Approve supplier invoices.",
    "input_schema": {
      "type": "object",
      "properties": {
        "invoiceIds": {
          "type": "string",
          "description": "ID of the elements"
        },
        "comment": {
          "type": "string",
          "description": "comment"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "supplier_invoice_change_dimension_change_dimension_many",
    "description": "Change dimension on a supplier invoice.",
    "input_schema": {
      "type": "object",
      "properties": {
        "invoiceId": {
          "type": "integer",
          "format": "int64",
          "description": "Invoice ID."
        },
        "debitPostingIds": {
          "type": "string",
          "description": "The list of IDs of the debit postings that you want to change dimensions for"
        },
        "dimension": {
          "type": "string",
          "enum": [
            "PROJECT",
            "DEPARTMENT",
            "EMPLOYEE",
            "PRODUCT",
            "FREE_DIMENSION_1",
            "FREE_DIMENSION_2",
            "FREE_DIMENSION_3"
          ],
          "description": "Dimension"
        },
        "dimensionId": {
          "type": "integer",
          "format": "int64",
          "description": "DimensionID"
        }
      },
      "required": [
        "invoiceId",
        "debitPostingIds",
        "dimension",
        "dimensionId"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "supplier_invoice_pdf_download_pdf",
    "description": "Get supplierInvoice document by invoice ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "invoiceId": {
          "type": "integer",
          "format": "int64",
          "description": "Invoice ID from which document is downloaded."
        }
      },
      "required": [
        "invoiceId"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "supplier_invoice_get",
    "description": "Get supplierInvoice by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "supplier_invoice_for_approval_get_approval_invoices",
    "description": "Get supplierInvoices for approval",
    "input_schema": {
      "type": "object",
      "properties": {
        "searchText": {
          "type": "string",
          "description": "Search for department, employee, project and more"
        },
        "showAll": {
          "type": "boolean",
          "default": false,
          "description": "Show all or just your own"
        },
        "employeeId": {
          "type": "integer",
          "format": "int64",
          "description": "Default is logged in employee"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "supplier_invoice_search",
    "description": "Find supplierInvoices corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "List of IDs"
        },
        "invoiceDateFrom": {
          "type": "string",
          "description": "From and including"
        },
        "invoiceDateTo": {
          "type": "string",
          "description": "To and excluding"
        },
        "invoiceNumber": {
          "type": "string",
          "description": "Equals"
        },
        "kid": {
          "type": "string",
          "description": "Equals"
        },
        "voucherId": {
          "type": "string",
          "description": "Equals"
        },
        "supplierId": {
          "type": "string",
          "description": "Equals"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "invoiceDateFrom",
        "invoiceDateTo"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "supplier_invoice_voucher_postings_put_postings",
    "description": "[BETA] Put debit postings.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Voucher id"
        },
        "sendToLedger": {
          "type": "boolean",
          "default": false,
          "description": "Use of this parameter with value 'true' requires setup done by Tripletex."
        },
        "voucherDate": {
          "type": "string",
          "description": "If set, the date of the voucher and the supplier invoice will be changed to this date. If empty, date will not be changed"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "supplier_invoice_reject_reject",
    "description": "reject supplier invoice.",
    "input_schema": {
      "type": "object",
      "properties": {
        "invoiceId": {
          "type": "integer",
          "format": "int64",
          "description": "Invoice ID."
        },
        "comment": {
          "type": "string",
          "description": "comment"
        }
      },
      "required": [
        "invoiceId",
        "comment"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "supplier_invoice_reject_reject_many",
    "description": "reject supplier invoices.",
    "input_schema": {
      "type": "object",
      "properties": {
        "comment": {
          "type": "string",
          "description": "comment"
        },
        "invoiceIds": {
          "type": "string",
          "description": "ID of the elements"
        }
      },
      "required": [
        "comment"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "timesheet_entry_get",
    "description": "Find timesheet entry by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "timesheet_entry_put",
    "description": "Update timesheet entry by ID. Note: Timesheet entry object fields which are present but not set, or set to 0, will be nulled.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "timesheet_entry_delete",
    "description": "Delete timesheet entry by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "version": {
          "type": "integer",
          "format": "int32",
          "description": "Number of current version"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "timesheet_entry_list_put_list",
    "description": "Update timesheet entry. Multiple objects for different users can be sent in the same request.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "timesheet_entry_list_post_list",
    "description": "Add new timesheet entry. Multiple objects for several users can be sent in the same request.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "timesheet_entry_search",
    "description": "Find timesheet entry corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "List of IDs"
        },
        "employeeId": {
          "type": "string",
          "description": "List of IDs"
        },
        "projectId": {
          "type": "string",
          "description": "List of IDs"
        },
        "activityId": {
          "type": "string",
          "description": "List of IDs"
        },
        "dateFrom": {
          "type": "string",
          "description": "From and including"
        },
        "dateTo": {
          "type": "string",
          "description": "To and excluding"
        },
        "comment": {
          "type": "string",
          "description": "Containing"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "dateFrom",
        "dateTo"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "timesheet_entry_post",
    "description": "Add new timesheet entry. Only one entry per employee/date/activity/project combination is supported.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "timesheet_entry_recent_activities_get_recent_activities",
    "description": "Find recently used timesheet activities.",
    "input_schema": {
      "type": "object",
      "properties": {
        "employeeId": {
          "type": "integer",
          "format": "int64",
          "description": "ID of employee to find activities for. Defaults to ID of token owner."
        },
        "projectId": {
          "type": "integer",
          "format": "int64",
          "description": "ID of project to find activities for"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "projectId"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "timesheet_entry_recent_projects_get_recent_projects",
    "description": "Find projects with recent activities (timesheet entry registered).",
    "input_schema": {
      "type": "object",
      "properties": {
        "employeeId": {
          "type": "integer",
          "format": "int64",
          "description": "ID of employee with recent project hours Defaults to ID of token owner."
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "timesheet_entry_total_hours_get_total_hours",
    "description": "Find total hours registered on an employee in a specific period.",
    "input_schema": {
      "type": "object",
      "properties": {
        "employeeId": {
          "type": "integer",
          "format": "int64",
          "description": "ID of employee to find hours for. Defaults to ID of token owner."
        },
        "startDate": {
          "type": "string",
          "description": "Format is yyyy-MM-dd (from and incl.). Defaults to today."
        },
        "endDate": {
          "type": "string",
          "description": "Format is yyyy-MM-dd (to and excl.). Defaults to tomorrow."
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_accommodation_allowance_get",
    "description": "Get travel accommodation allowance by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_accommodation_allowance_put",
    "description": "Update accommodation allowance.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_accommodation_allowance_delete",
    "description": "Delete accommodation allowance.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_accommodation_allowance_search",
    "description": "Find accommodation allowances corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "travelExpenseId": {
          "type": "string",
          "description": "Equals"
        },
        "rateTypeId": {
          "type": "string",
          "description": "Equals"
        },
        "rateCategoryId": {
          "type": "string",
          "description": "Equals"
        },
        "rateFrom": {
          "type": "number",
          "description": "From and including"
        },
        "rateTo": {
          "type": "number",
          "description": "To and excluding"
        },
        "countFrom": {
          "type": "integer",
          "format": "int32",
          "description": "From and including"
        },
        "countTo": {
          "type": "integer",
          "format": "int32",
          "description": "To and excluding"
        },
        "amountFrom": {
          "type": "number",
          "description": "From and including"
        },
        "amountTo": {
          "type": "number",
          "description": "To and excluding"
        },
        "location": {
          "type": "string",
          "description": "Containing"
        },
        "address": {
          "type": "string",
          "description": "Containing"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_accommodation_allowance_post",
    "description": "Create accommodation allowance.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_cost_get",
    "description": "Get cost by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_cost_put",
    "description": "Update cost.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_cost_delete",
    "description": "Delete cost.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_cost_search",
    "description": "Find costs corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "travelExpenseId": {
          "type": "string",
          "description": "Equals"
        },
        "vatTypeId": {
          "type": "string",
          "description": "Equals"
        },
        "currencyId": {
          "type": "string",
          "description": "Equals"
        },
        "rateFrom": {
          "type": "number",
          "description": "From and including"
        },
        "rateTo": {
          "type": "number",
          "description": "To and excluding"
        },
        "countFrom": {
          "type": "integer",
          "format": "int32",
          "description": "From and including"
        },
        "countTo": {
          "type": "integer",
          "format": "int32",
          "description": "To and excluding"
        },
        "amountFrom": {
          "type": "number",
          "description": "From and including"
        },
        "amountTo": {
          "type": "number",
          "description": "To and excluding"
        },
        "location": {
          "type": "string",
          "description": "Containing"
        },
        "address": {
          "type": "string",
          "description": "Containing"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_cost_post",
    "description": "Create cost.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_cost_list_put_list",
    "description": "Update costs.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_mileage_allowance_get",
    "description": "Get mileage allowance by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_mileage_allowance_put",
    "description": "Update mileage allowance.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_mileage_allowance_delete",
    "description": "Delete mileage allowance.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_mileage_allowance_search",
    "description": "Find mileage allowances corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "travelExpenseId": {
          "type": "string",
          "description": "Equals"
        },
        "rateTypeId": {
          "type": "string",
          "description": "Equals"
        },
        "rateCategoryId": {
          "type": "string",
          "description": "Equals"
        },
        "kmFrom": {
          "type": "number",
          "description": "From and including"
        },
        "kmTo": {
          "type": "number",
          "description": "To and excluding"
        },
        "rateFrom": {
          "type": "number",
          "description": "From and including"
        },
        "rateTo": {
          "type": "number",
          "description": "To and excluding"
        },
        "amountFrom": {
          "type": "number",
          "description": "From and including"
        },
        "amountTo": {
          "type": "number",
          "description": "To and excluding"
        },
        "departureLocation": {
          "type": "string",
          "description": "Containing"
        },
        "destination": {
          "type": "string",
          "description": "Containing"
        },
        "dateFrom": {
          "type": "string",
          "description": "From and including"
        },
        "dateTo": {
          "type": "string",
          "description": "To and excluding"
        },
        "isCompanyCar": {
          "type": "boolean",
          "description": "Equals"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_mileage_allowance_post",
    "description": "Create mileage allowance.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_per_diem_compensation_get",
    "description": "Get per diem compensation by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_per_diem_compensation_put",
    "description": "Update per diem compensation.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_per_diem_compensation_delete",
    "description": "Delete per diem compensation.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_per_diem_compensation_search",
    "description": "Find per diem compensations corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "travelExpenseId": {
          "type": "string",
          "description": "Equals"
        },
        "rateTypeId": {
          "type": "string",
          "description": "Equals"
        },
        "rateCategoryId": {
          "type": "string",
          "description": "Equals"
        },
        "overnightAccommodation": {
          "type": "string",
          "enum": [
            "NONE",
            "HOTEL",
            "BOARDING_HOUSE_WITHOUT_COOKING",
            "BOARDING_HOUSE_WITH_COOKING"
          ],
          "description": "Equals"
        },
        "countFrom": {
          "type": "integer",
          "format": "int32",
          "description": "From and including"
        },
        "countTo": {
          "type": "integer",
          "format": "int32",
          "description": "To and excluding"
        },
        "rateFrom": {
          "type": "number",
          "description": "From and including"
        },
        "rateTo": {
          "type": "number",
          "description": "To and excluding"
        },
        "amountFrom": {
          "type": "number",
          "description": "From and including"
        },
        "amountTo": {
          "type": "number",
          "description": "To and excluding"
        },
        "location": {
          "type": "string",
          "description": "Containing"
        },
        "address": {
          "type": "string",
          "description": "Containing"
        },
        "isDeductionForBreakfast": {
          "type": "boolean",
          "description": "Equals"
        },
        "isLunchDeduction": {
          "type": "boolean",
          "description": "Equals"
        },
        "isDinnerDeduction": {
          "type": "boolean",
          "description": "Equals"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_per_diem_compensation_post",
    "description": "Create per diem compensation.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_approve_approve",
    "description": "Approve travel expenses.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "ID of the elements"
        },
        "overrideApprovalFlow": {
          "type": "boolean",
          "default": false,
          "description": "Override approval flow"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_convert_convert",
    "description": "Convert travel to/from employee expense.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_copy_copy",
    "description": "Copy travel expense.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_create_vouchers_create_vouchers",
    "description": "Create vouchers",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "ID of the elements"
        },
        "date": {
          "type": "string",
          "description": "yyyy-MM-dd. Defaults to today."
        }
      },
      "required": [
        "date"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_get",
    "description": "Get travel expense by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_put",
    "description": "Update travel expense.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_delete",
    "description": "Delete travel expense.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_attachment_download_attachment",
    "description": "Get attachment by travel expense ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "travelExpenseId": {
          "type": "integer",
          "format": "int64",
          "description": "Travel Expense ID from which PDF is downloaded."
        }
      },
      "required": [
        "travelExpenseId"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_attachment_upload_attachment",
    "description": "Upload attachment to travel expense.",
    "input_schema": {
      "type": "object",
      "properties": {
        "travelExpenseId": {
          "type": "integer",
          "format": "int64",
          "description": "Travel Expense ID to upload attachment to."
        },
        "createNewCost": {
          "type": "boolean",
          "default": false,
          "description": "Create new cost row when you add the attachment"
        }
      },
      "required": [
        "travelExpenseId"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_attachment_delete_attachment",
    "description": "Delete attachment.",
    "input_schema": {
      "type": "object",
      "properties": {
        "travelExpenseId": {
          "type": "integer",
          "format": "int64",
          "description": "ID of attachment containing the attachment to delete."
        },
        "version": {
          "minimum": 0,
          "type": "integer",
          "format": "int32",
          "description": "Version of voucher containing the attachment to delete."
        },
        "sendToInbox": {
          "type": "boolean",
          "default": false,
          "description": "Should the attachment be sent to inbox rather than deleted?"
        },
        "split": {
          "type": "boolean",
          "default": false,
          "description": "If sendToInbox is true, should the attachment be split into one voucher per page?"
        }
      },
      "required": [
        "travelExpenseId"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_deliver_deliver",
    "description": "Deliver travel expenses.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "ID of the elements"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_search",
    "description": "Find travel expenses corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "employeeId": {
          "type": "string",
          "description": "Equals"
        },
        "departmentId": {
          "type": "string",
          "description": "Equals"
        },
        "projectId": {
          "type": "string",
          "description": "Equals"
        },
        "projectManagerId": {
          "type": "string",
          "description": "Equals"
        },
        "departureDateFrom": {
          "type": "string",
          "description": "From and including"
        },
        "returnDateTo": {
          "type": "string",
          "description": "To and excluding"
        },
        "state": {
          "type": "string",
          "enum": [
            "ALL",
            "REJECTED",
            "OPEN",
            "APPROVED",
            "SALARY_PAID",
            "DELIVERED"
          ],
          "default": "ALL",
          "description": "category"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_post",
    "description": "Create travel expense.",
    "input_schema": {
      "type": "object",
      "properties": {}
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_unapprove_unapprove",
    "description": "Unapprove travel expenses.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "ID of the elements"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_undeliver_undeliver",
    "description": "Undeliver travel expenses.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "ID of the elements"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_attachment_list_upload_attachments",
    "description": "Upload multiple attachments to travel expense.",
    "input_schema": {
      "type": "object",
      "properties": {
        "travelExpenseId": {
          "type": "integer",
          "format": "int64",
          "description": "Travel Expense ID to upload attachment to."
        },
        "createNewCost": {
          "type": "boolean",
          "default": false,
          "description": "Create new cost row when you add the attachment"
        }
      },
      "required": [
        "travelExpenseId"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_rate_get",
    "description": "Get travel expense rate by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_rate_search",
    "description": "Find rates corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "rateCategoryId": {
          "type": "string",
          "description": "Equals"
        },
        "type": {
          "type": "string",
          "enum": [
            "PER_DIEM",
            "ACCOMMODATION_ALLOWANCE",
            "MILEAGE_ALLOWANCE"
          ],
          "description": "Equals"
        },
        "isValidDayTrip": {
          "type": "boolean",
          "description": "Equals"
        },
        "isValidAccommodation": {
          "type": "boolean",
          "description": "Equals"
        },
        "isValidDomestic": {
          "type": "boolean",
          "description": "Equals"
        },
        "isValidForeignTravel": {
          "type": "boolean",
          "description": "Equals"
        },
        "requiresZone": {
          "type": "boolean",
          "description": "Equals"
        },
        "requiresOvernightAccommodation": {
          "type": "boolean",
          "description": "Equals"
        },
        "dateFrom": {
          "type": "string",
          "description": "From and including"
        },
        "dateTo": {
          "type": "string",
          "description": "To and excluding"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_rate_category_get",
    "description": "Get travel expense rate category by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_rate_category_search",
    "description": "Find rate categories corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "type": {
          "type": "string",
          "enum": [
            "PER_DIEM",
            "ACCOMMODATION_ALLOWANCE",
            "MILEAGE_ALLOWANCE"
          ],
          "description": "Equals"
        },
        "name": {
          "type": "string",
          "description": "Containing"
        },
        "travelReportRateCategoryGroupId": {
          "type": "integer",
          "format": "int64",
          "description": "Equals"
        },
        "ameldingWageCode": {
          "type": "string",
          "description": "Containing"
        },
        "wageCodeNumber": {
          "type": "string",
          "description": "Equals"
        },
        "isValidDayTrip": {
          "type": "boolean",
          "description": "Equals"
        },
        "isValidAccommodation": {
          "type": "boolean",
          "description": "Equals"
        },
        "isValidDomestic": {
          "type": "boolean",
          "description": "Equals"
        },
        "requiresZone": {
          "type": "boolean",
          "description": "Equals"
        },
        "isRequiresOvernightAccommodation": {
          "type": "boolean",
          "description": "Equals"
        },
        "dateFrom": {
          "type": "string",
          "description": "From and including"
        },
        "dateTo": {
          "type": "string",
          "description": "To and excluding"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_cost_category_get",
    "description": "Get cost category by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_cost_category_search",
    "description": "Find cost category corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "List of IDs"
        },
        "description": {
          "type": "string",
          "description": "Containing"
        },
        "isInactive": {
          "type": "boolean",
          "description": "Equals"
        },
        "showOnEmployeeExpenses": {
          "type": "boolean",
          "description": "Equals"
        },
        "query": {
          "type": "string",
          "description": "Equals"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_payment_type_get",
    "description": "Get payment type by ID.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "integer",
          "format": "int64",
          "description": "Element ID"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      },
      "required": [
        "id"
      ]
    },
    "defer_loading": true
  },
  {
    "name": "travel_expense_payment_type_search",
    "description": "Find payment type corresponding with sent data.",
    "input_schema": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "List of IDs"
        },
        "description": {
          "type": "string",
          "description": "Containing"
        },
        "isInactive": {
          "type": "boolean",
          "description": "Equals"
        },
        "showOnEmployeeExpenses": {
          "type": "boolean",
          "description": "Equals"
        },
        "query": {
          "type": "string",
          "description": "Containing"
        },
        "from": {
          "type": "integer",
          "default": "0",
          "description": "From index"
        },
        "count": {
          "type": "integer",
          "default": "1000",
          "description": "Number of elements to return"
        },
        "sorting": {
          "type": "string",
          "default": "",
          "description": "Sorting pattern"
        },
        "fields": {
          "type": "string",
          "default": "",
          "description": "Fields filter pattern"
        }
      }
    },
    "defer_loading": true
  }
]

GENERATED_TOOLS_META = {
  "activity_get": {
    "method": "GET",
    "path": "/activity/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "activity_list_post_list": {
    "method": "POST",
    "path": "/activity/list",
    "path_params": [],
    "query_params": []
  },
  "activity_for_time_sheet_get_for_time_sheet": {
    "method": "GET",
    "path": "/activity/>forTimeSheet",
    "path_params": [],
    "query_params": [
      "projectId",
      "employeeId",
      "date",
      "filterExistingHours",
      "query",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "activity_search": {
    "method": "GET",
    "path": "/activity",
    "path_params": [],
    "query_params": [
      "id",
      "name",
      "number",
      "description",
      "isProjectActivity",
      "isGeneral",
      "isChargeable",
      "isTask",
      "isInactive",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "activity_post": {
    "method": "POST",
    "path": "/activity",
    "path_params": [],
    "query_params": []
  },
  "delivery_address_get": {
    "method": "GET",
    "path": "/deliveryAddress/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "delivery_address_put": {
    "method": "PUT",
    "path": "/deliveryAddress/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "delivery_address_search": {
    "method": "GET",
    "path": "/deliveryAddress",
    "path_params": [],
    "query_params": [
      "id",
      "addressLine1",
      "addressLine2",
      "postalCode",
      "city",
      "name",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "asset_balance_accounts_sum_balance_accounts_sum": {
    "method": "GET",
    "path": "/asset/balanceAccountsSum",
    "path_params": [],
    "query_params": [
      "fields"
    ]
  },
  "asset_can_delete_can_delete": {
    "method": "GET",
    "path": "/asset/canDelete/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "asset_get": {
    "method": "GET",
    "path": "/asset/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "asset_put": {
    "method": "PUT",
    "path": "/asset/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "asset_delete": {
    "method": "DELETE",
    "path": "/asset/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "asset_list_post_list": {
    "method": "POST",
    "path": "/asset/list",
    "path_params": [],
    "query_params": []
  },
  "asset_delete_import_delete_import": {
    "method": "DELETE",
    "path": "/asset/deleteImport",
    "path_params": [],
    "query_params": []
  },
  "asset_delete_starting_balance_delete_starting_balance": {
    "method": "DELETE",
    "path": "/asset/deleteStartingBalance",
    "path_params": [],
    "query_params": []
  },
  "asset_assets_exist_get_assets_exist": {
    "method": "GET",
    "path": "/asset/assetsExist",
    "path_params": [],
    "query_params": [
      "fields"
    ]
  },
  "asset_postings_get_postings": {
    "method": "GET",
    "path": "/asset/{id}/postings",
    "path_params": [
      "id"
    ],
    "query_params": [
      "dateFrom",
      "dateToExclusive",
      "fields",
      "from",
      "count",
      "sorting"
    ]
  },
  "asset_search": {
    "method": "GET",
    "path": "/asset",
    "path_params": [],
    "query_params": [
      "id",
      "name",
      "description",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "asset_post": {
    "method": "POST",
    "path": "/asset",
    "path_params": [],
    "query_params": []
  },
  "asset_duplicate_post_duplicate": {
    "method": "POST",
    "path": "/asset/duplicate/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "asset_upload_upload": {
    "method": "POST",
    "path": "/asset/upload",
    "path_params": [],
    "query_params": [
      "isPreview",
      "startDate"
    ]
  },
  "balance_sheet_search": {
    "method": "GET",
    "path": "/balanceSheet",
    "path_params": [],
    "query_params": [
      "dateFrom",
      "dateTo",
      "accountNumberFrom",
      "accountNumberTo",
      "customerId",
      "employeeId",
      "departmentId",
      "projectId",
      "includeSubProjects",
      "includeActiveAccountsWithoutMovements",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "bank_reconciliation_adjustment_adjustment": {
    "method": "PUT",
    "path": "/bank/reconciliation/{id}/:adjustment",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "bank_reconciliation_closed_with_unmatched_transactions_closed_with_unmatched_transactions": {
    "method": "GET",
    "path": "/bank/reconciliation/closedWithUnmatchedTransactions",
    "path_params": [],
    "query_params": [
      "accountId",
      "start",
      "fields"
    ]
  },
  "bank_reconciliation_transactions_unmatchedcsv_csv_transactions": {
    "method": "PUT",
    "path": "/bank/reconciliation/transactions/unmatched:csv",
    "path_params": [],
    "query_params": [
      "reconciliationId"
    ]
  },
  "bank_reconciliation_get": {
    "method": "GET",
    "path": "/bank/reconciliation/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "bank_reconciliation_put": {
    "method": "PUT",
    "path": "/bank/reconciliation/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "bank_reconciliation_delete": {
    "method": "DELETE",
    "path": "/bank/reconciliation/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "bank_reconciliation_last_last": {
    "method": "GET",
    "path": "/bank/reconciliation/>last",
    "path_params": [],
    "query_params": [
      "accountId",
      "fields"
    ]
  },
  "bank_reconciliation_last_closed_last_closed": {
    "method": "GET",
    "path": "/bank/reconciliation/>lastClosed",
    "path_params": [],
    "query_params": [
      "accountId",
      "after",
      "fields"
    ]
  },
  "bank_reconciliation_search": {
    "method": "GET",
    "path": "/bank/reconciliation",
    "path_params": [],
    "query_params": [
      "id",
      "accountingPeriodId",
      "accountId",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "bank_reconciliation_post": {
    "method": "POST",
    "path": "/bank/reconciliation",
    "path_params": [],
    "query_params": []
  },
  "bank_reconciliation_match_count_count": {
    "method": "GET",
    "path": "/bank/reconciliation/match/count",
    "path_params": [],
    "query_params": [
      "bankReconciliationId",
      "fields"
    ]
  },
  "bank_reconciliation_match_get": {
    "method": "GET",
    "path": "/bank/reconciliation/match/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "bank_reconciliation_match_put": {
    "method": "PUT",
    "path": "/bank/reconciliation/match/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "bank_reconciliation_match_delete": {
    "method": "DELETE",
    "path": "/bank/reconciliation/match/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "bank_reconciliation_match_search": {
    "method": "GET",
    "path": "/bank/reconciliation/match",
    "path_params": [],
    "query_params": [
      "id",
      "bankReconciliationId",
      "count",
      "approved",
      "from",
      "sorting",
      "fields"
    ]
  },
  "bank_reconciliation_match_post": {
    "method": "POST",
    "path": "/bank/reconciliation/match",
    "path_params": [],
    "query_params": []
  },
  "bank_reconciliation_match_query_query": {
    "method": "GET",
    "path": "/bank/reconciliation/match/query",
    "path_params": [],
    "query_params": [
      "bankReconciliationId",
      "approved",
      "count",
      "from",
      "sorting",
      "fields"
    ]
  },
  "bank_reconciliation_match_suggest_suggest": {
    "method": "PUT",
    "path": "/bank/reconciliation/match/:suggest",
    "path_params": [],
    "query_params": [
      "bankReconciliationId"
    ]
  },
  "bank_reconciliation_matches_counter_get": {
    "method": "GET",
    "path": "/bank/reconciliation/matches/counter",
    "path_params": [],
    "query_params": [
      "bankReconciliationId",
      "fields"
    ]
  },
  "bank_reconciliation_matches_counter_post": {
    "method": "POST",
    "path": "/bank/reconciliation/matches/counter",
    "path_params": [],
    "query_params": [
      "bankReconciliationId"
    ]
  },
  "company_with_login_access_get_with_login_access": {
    "method": "GET",
    "path": "/company/>withLoginAccess",
    "path_params": [],
    "query_params": [
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "company_get": {
    "method": "GET",
    "path": "/company/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "company_divisions_get_divisions": {
    "method": "GET",
    "path": "/company/divisions",
    "path_params": [],
    "query_params": [
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "company_put": {
    "method": "PUT",
    "path": "/company",
    "path_params": [],
    "query_params": []
  },
  "contact_get": {
    "method": "GET",
    "path": "/contact/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "contact_put": {
    "method": "PUT",
    "path": "/contact/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "contact_list_post_list": {
    "method": "POST",
    "path": "/contact/list",
    "path_params": [],
    "query_params": []
  },
  "contact_list_delete_by_ids": {
    "method": "DELETE",
    "path": "/contact/list",
    "path_params": [],
    "query_params": [
      "ids"
    ]
  },
  "contact_search": {
    "method": "GET",
    "path": "/contact",
    "path_params": [],
    "query_params": [
      "id",
      "firstName",
      "lastName",
      "email",
      "customerId",
      "departmentId",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "contact_post": {
    "method": "POST",
    "path": "/contact",
    "path_params": [],
    "query_params": []
  },
  "country_get": {
    "method": "GET",
    "path": "/country/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "country_search": {
    "method": "GET",
    "path": "/country",
    "path_params": [],
    "query_params": [
      "id",
      "code",
      "isDisabled",
      "supportedInZtl",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "currency_get": {
    "method": "GET",
    "path": "/currency/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "currency_search": {
    "method": "GET",
    "path": "/currency",
    "path_params": [],
    "query_params": [
      "id",
      "code",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "currency_exchange_rate_convert_currency_amount": {
    "method": "GET",
    "path": "/currency/{fromCurrencyID}/{toCurrencyID}/exchangeRate",
    "path_params": [
      "fromCurrencyID",
      "toCurrencyID"
    ],
    "query_params": [
      "amount",
      "date",
      "fields"
    ]
  },
  "currency_exchange_rate_get_amount_currency": {
    "method": "GET",
    "path": "/currency/{fromCurrencyID}/exchangeRate",
    "path_params": [
      "fromCurrencyID"
    ],
    "query_params": [
      "amount",
      "date",
      "fields"
    ]
  },
  "currency_rate_get_rate": {
    "method": "GET",
    "path": "/currency/{id}/rate",
    "path_params": [
      "id"
    ],
    "query_params": [
      "date",
      "fields"
    ]
  },
  "customer_get": {
    "method": "GET",
    "path": "/customer/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "customer_put": {
    "method": "PUT",
    "path": "/customer/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "customer_delete": {
    "method": "DELETE",
    "path": "/customer/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "customer_search": {
    "method": "GET",
    "path": "/customer",
    "path_params": [],
    "query_params": [
      "id",
      "customerAccountNumber",
      "organizationNumber",
      "email",
      "invoiceEmail",
      "customerName",
      "phoneNumberMobile",
      "isInactive",
      "accountManagerId",
      "changedSince",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "customer_post": {
    "method": "POST",
    "path": "/customer",
    "path_params": [],
    "query_params": []
  },
  "customer_list_put_list": {
    "method": "PUT",
    "path": "/customer/list",
    "path_params": [],
    "query_params": []
  },
  "customer_list_post_list": {
    "method": "POST",
    "path": "/customer/list",
    "path_params": [],
    "query_params": []
  },
  "customer_category_get": {
    "method": "GET",
    "path": "/customer/category/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "customer_category_put": {
    "method": "PUT",
    "path": "/customer/category/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "customer_category_search": {
    "method": "GET",
    "path": "/customer/category",
    "path_params": [],
    "query_params": [
      "id",
      "name",
      "number",
      "description",
      "type",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "customer_category_post": {
    "method": "POST",
    "path": "/customer/category",
    "path_params": [],
    "query_params": []
  },
  "department_get": {
    "method": "GET",
    "path": "/department/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "department_put": {
    "method": "PUT",
    "path": "/department/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "department_delete": {
    "method": "DELETE",
    "path": "/department/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "department_search": {
    "method": "GET",
    "path": "/department",
    "path_params": [],
    "query_params": [
      "id",
      "name",
      "departmentNumber",
      "departmentManagerId",
      "isInactive",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "department_post": {
    "method": "POST",
    "path": "/department",
    "path_params": [],
    "query_params": []
  },
  "department_list_put_list": {
    "method": "PUT",
    "path": "/department/list",
    "path_params": [],
    "query_params": []
  },
  "department_list_post_list": {
    "method": "POST",
    "path": "/department/list",
    "path_params": [],
    "query_params": []
  },
  "department_query_query": {
    "method": "GET",
    "path": "/department/query",
    "path_params": [],
    "query_params": [
      "id",
      "query",
      "count",
      "fields",
      "isInactive",
      "from",
      "sorting"
    ]
  },
  "division_search": {
    "method": "GET",
    "path": "/division",
    "path_params": [],
    "query_params": [
      "query",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "division_post": {
    "method": "POST",
    "path": "/division",
    "path_params": [],
    "query_params": []
  },
  "division_list_put_list": {
    "method": "PUT",
    "path": "/division/list",
    "path_params": [],
    "query_params": []
  },
  "division_list_post_list": {
    "method": "POST",
    "path": "/division/list",
    "path_params": [],
    "query_params": []
  },
  "division_put": {
    "method": "PUT",
    "path": "/division/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "employee_get": {
    "method": "GET",
    "path": "/employee/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "employee_put": {
    "method": "PUT",
    "path": "/employee/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "employee_list_post_list": {
    "method": "POST",
    "path": "/employee/list",
    "path_params": [],
    "query_params": []
  },
  "employee_search": {
    "method": "GET",
    "path": "/employee",
    "path_params": [],
    "query_params": [
      "id",
      "firstName",
      "lastName",
      "employeeNumber",
      "email",
      "allowInformationRegistration",
      "includeContacts",
      "departmentId",
      "onlyProjectManagers",
      "onlyContacts",
      "assignableProjectManagers",
      "periodStart",
      "periodEnd",
      "hasSystemAccess",
      "onlyEmployeeTokens",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "employee_post": {
    "method": "POST",
    "path": "/employee",
    "path_params": [],
    "query_params": []
  },
  "employee_search_for_employees_and_contacts_search_for_employees_and_contacts": {
    "method": "GET",
    "path": "/employee/searchForEmployeesAndContacts",
    "path_params": [],
    "query_params": [
      "id",
      "firstName",
      "lastName",
      "email",
      "includeContacts",
      "isInactive",
      "hasSystemAccess",
      "excludeReadOnly",
      "fields",
      "from",
      "count",
      "sorting"
    ]
  },
  "employee_employment_get": {
    "method": "GET",
    "path": "/employee/employment/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "employee_employment_put": {
    "method": "PUT",
    "path": "/employee/employment/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "employee_employment_search": {
    "method": "GET",
    "path": "/employee/employment",
    "path_params": [],
    "query_params": [
      "employeeId",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "employee_employment_post": {
    "method": "POST",
    "path": "/employee/employment",
    "path_params": [],
    "query_params": []
  },
  "employee_employment_details_get": {
    "method": "GET",
    "path": "/employee/employment/details/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "employee_employment_details_put": {
    "method": "PUT",
    "path": "/employee/employment/details/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "employee_employment_details_search": {
    "method": "GET",
    "path": "/employee/employment/details",
    "path_params": [],
    "query_params": [
      "employmentId",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "employee_employment_details_post": {
    "method": "POST",
    "path": "/employee/employment/details",
    "path_params": [],
    "query_params": []
  },
  "employee_entitlement_client_client": {
    "method": "GET",
    "path": "/employee/entitlement/client",
    "path_params": [],
    "query_params": [
      "employeeId",
      "customerId",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "employee_entitlement_get": {
    "method": "GET",
    "path": "/employee/entitlement/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "employee_entitlement_grant_client_entitlements_by_template_grant_client_entitlements_by_template": {
    "method": "PUT",
    "path": "/employee/entitlement/:grantClientEntitlementsByTemplate",
    "path_params": [],
    "query_params": [
      "employeeId",
      "customerId",
      "template",
      "addToExisting"
    ]
  },
  "employee_entitlement_grant_entitlements_by_template_grant_entitlements_by_template": {
    "method": "PUT",
    "path": "/employee/entitlement/:grantEntitlementsByTemplate",
    "path_params": [],
    "query_params": [
      "employeeId",
      "template"
    ]
  },
  "employee_entitlement_search": {
    "method": "GET",
    "path": "/employee/entitlement",
    "path_params": [],
    "query_params": [
      "employeeId",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "incoming_invoice_add_payment_add_payment": {
    "method": "POST",
    "path": "/incomingInvoice/{voucherId}/addPayment",
    "path_params": [
      "voucherId"
    ],
    "query_params": []
  },
  "incoming_invoice_get": {
    "method": "GET",
    "path": "/incomingInvoice/{voucherId}",
    "path_params": [
      "voucherId"
    ],
    "query_params": [
      "fields"
    ]
  },
  "incoming_invoice_put": {
    "method": "PUT",
    "path": "/incomingInvoice/{voucherId}",
    "path_params": [
      "voucherId"
    ],
    "query_params": [
      "sendTo"
    ]
  },
  "incoming_invoice_post": {
    "method": "POST",
    "path": "/incomingInvoice",
    "path_params": [],
    "query_params": [
      "sendTo"
    ]
  },
  "incoming_invoice_search_search": {
    "method": "GET",
    "path": "/incomingInvoice/search",
    "path_params": [],
    "query_params": [
      "voucherId",
      "invoiceDateFrom",
      "invoiceDateTo",
      "invoiceNumber",
      "vendorId",
      "status",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "inventory_get": {
    "method": "GET",
    "path": "/inventory/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "inventory_put": {
    "method": "PUT",
    "path": "/inventory/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "inventory_delete": {
    "method": "DELETE",
    "path": "/inventory/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "inventory_search": {
    "method": "GET",
    "path": "/inventory",
    "path_params": [],
    "query_params": [
      "id",
      "name",
      "isMainInventory",
      "isInactive",
      "query",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "inventory_post": {
    "method": "POST",
    "path": "/inventory",
    "path_params": [],
    "query_params": []
  },
  "inventory_location_get": {
    "method": "GET",
    "path": "/inventory/location/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "inventory_location_put": {
    "method": "PUT",
    "path": "/inventory/location/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "inventory_location_delete": {
    "method": "DELETE",
    "path": "/inventory/location/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "inventory_location_list_put_list": {
    "method": "PUT",
    "path": "/inventory/location/list",
    "path_params": [],
    "query_params": []
  },
  "inventory_location_list_post_list": {
    "method": "POST",
    "path": "/inventory/location/list",
    "path_params": [],
    "query_params": []
  },
  "inventory_location_list_delete_by_ids": {
    "method": "DELETE",
    "path": "/inventory/location/list",
    "path_params": [],
    "query_params": [
      "ids"
    ]
  },
  "inventory_location_search": {
    "method": "GET",
    "path": "/inventory/location",
    "path_params": [],
    "query_params": [
      "warehouseId",
      "isInactive",
      "name",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "inventory_location_post": {
    "method": "POST",
    "path": "/inventory/location",
    "path_params": [],
    "query_params": []
  },
  "invoice_create_credit_note_create_credit_note": {
    "method": "PUT",
    "path": "/invoice/{id}/:createCreditNote",
    "path_params": [
      "id"
    ],
    "query_params": [
      "date",
      "comment",
      "creditNoteEmail",
      "sendToCustomer",
      "sendType"
    ]
  },
  "invoice_create_reminder_create_reminder": {
    "method": "PUT",
    "path": "/invoice/{id}/:createReminder",
    "path_params": [
      "id"
    ],
    "query_params": [
      "type",
      "date",
      "includeCharge",
      "includeInterest",
      "dispatchType",
      "dispatchTypes",
      "smsNumber",
      "email",
      "address",
      "postalCode",
      "city"
    ]
  },
  "invoice_get": {
    "method": "GET",
    "path": "/invoice/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "invoice_pdf_download_pdf": {
    "method": "GET",
    "path": "/invoice/{invoiceId}/pdf",
    "path_params": [
      "invoiceId"
    ],
    "query_params": [
      "download"
    ]
  },
  "invoice_payment_payment": {
    "method": "PUT",
    "path": "/invoice/{id}/:payment",
    "path_params": [
      "id"
    ],
    "query_params": [
      "paymentDate",
      "paymentTypeId",
      "paidAmount",
      "paidAmountCurrency"
    ]
  },
  "invoice_search": {
    "method": "GET",
    "path": "/invoice",
    "path_params": [],
    "query_params": [
      "id",
      "invoiceDateFrom",
      "invoiceDateTo",
      "invoiceNumber",
      "kid",
      "voucherId",
      "customerId",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "invoice_post": {
    "method": "POST",
    "path": "/invoice",
    "path_params": [],
    "query_params": [
      "sendToCustomer",
      "paymentTypeId",
      "paidAmount"
    ]
  },
  "invoice_list_post_list": {
    "method": "POST",
    "path": "/invoice/list",
    "path_params": [],
    "query_params": [
      "sendToCustomer",
      "fields"
    ]
  },
  "invoice_send_send": {
    "method": "PUT",
    "path": "/invoice/{id}/:send",
    "path_params": [
      "id"
    ],
    "query_params": [
      "sendType",
      "overrideEmailAddress"
    ]
  },
  "ledger_account_get": {
    "method": "GET",
    "path": "/ledger/account/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "ledger_account_put": {
    "method": "PUT",
    "path": "/ledger/account/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "ledger_account_delete": {
    "method": "DELETE",
    "path": "/ledger/account/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "ledger_account_list_put_list": {
    "method": "PUT",
    "path": "/ledger/account/list",
    "path_params": [],
    "query_params": []
  },
  "ledger_account_list_post_list": {
    "method": "POST",
    "path": "/ledger/account/list",
    "path_params": [],
    "query_params": []
  },
  "ledger_account_list_delete_by_ids": {
    "method": "DELETE",
    "path": "/ledger/account/list",
    "path_params": [],
    "query_params": [
      "ids"
    ]
  },
  "ledger_account_search": {
    "method": "GET",
    "path": "/ledger/account",
    "path_params": [],
    "query_params": [
      "id",
      "number",
      "isBankAccount",
      "isInactive",
      "isApplicableForSupplierInvoice",
      "ledgerType",
      "isBalanceAccount",
      "saftCode",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "ledger_account_post": {
    "method": "POST",
    "path": "/ledger/account",
    "path_params": [],
    "query_params": []
  },
  "ledger_posting_close_postings_close_postings": {
    "method": "PUT",
    "path": "/ledger/posting/:closePostings",
    "path_params": [],
    "query_params": []
  },
  "ledger_posting_get": {
    "method": "GET",
    "path": "/ledger/posting/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "ledger_posting_open_post_open_post": {
    "method": "GET",
    "path": "/ledger/posting/openPost",
    "path_params": [],
    "query_params": [
      "date",
      "accountId",
      "supplierId",
      "customerId",
      "employeeId",
      "departmentId",
      "projectId",
      "productId",
      "accountNumberFrom",
      "accountNumberTo",
      "accountingDimensionValue1Id",
      "accountingDimensionValue2Id",
      "accountingDimensionValue3Id",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "ledger_posting_search": {
    "method": "GET",
    "path": "/ledger/posting",
    "path_params": [],
    "query_params": [
      "dateFrom",
      "dateTo",
      "openPostings",
      "accountId",
      "supplierId",
      "customerId",
      "employeeId",
      "departmentId",
      "projectId",
      "productId",
      "accountNumberFrom",
      "accountNumberTo",
      "type",
      "accountingDimensionValue1Id",
      "accountingDimensionValue2Id",
      "accountingDimensionValue3Id",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "ledger_vat_type_create_relative_vat_type_create_relative_vat_type": {
    "method": "PUT",
    "path": "/ledger/vatType/createRelativeVatType",
    "path_params": [],
    "query_params": [
      "name",
      "vatTypeId",
      "percentage"
    ]
  },
  "ledger_vat_type_get": {
    "method": "GET",
    "path": "/ledger/vatType/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "ledger_vat_type_search": {
    "method": "GET",
    "path": "/ledger/vatType",
    "path_params": [],
    "query_params": [
      "id",
      "number",
      "typeOfVat",
      "vatDate",
      "shouldIncludeSpecificationTypes",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "ledger_voucher_get": {
    "method": "GET",
    "path": "/ledger/voucher/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "ledger_voucher_put": {
    "method": "PUT",
    "path": "/ledger/voucher/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "sendToLedger"
    ]
  },
  "ledger_voucher_delete": {
    "method": "DELETE",
    "path": "/ledger/voucher/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "ledger_voucher_attachment_upload_attachment": {
    "method": "POST",
    "path": "/ledger/voucher/{voucherId}/attachment",
    "path_params": [
      "voucherId"
    ],
    "query_params": []
  },
  "ledger_voucher_attachment_delete_attachment": {
    "method": "DELETE",
    "path": "/ledger/voucher/{voucherId}/attachment",
    "path_params": [
      "voucherId"
    ],
    "query_params": [
      "version",
      "sendToInbox",
      "split"
    ]
  },
  "ledger_voucher_pdf_download_pdf": {
    "method": "GET",
    "path": "/ledger/voucher/{voucherId}/pdf",
    "path_params": [
      "voucherId"
    ],
    "query_params": []
  },
  "ledger_voucher_external_voucher_number_external_voucher_number": {
    "method": "GET",
    "path": "/ledger/voucher/>externalVoucherNumber",
    "path_params": [],
    "query_params": [
      "externalVoucherNumber",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "ledger_voucher_import_document_import_document": {
    "method": "POST",
    "path": "/ledger/voucher/importDocument",
    "path_params": [],
    "query_params": [
      "split"
    ]
  },
  "ledger_voucher_import_gbat10_import_gbat10": {
    "method": "POST",
    "path": "/ledger/voucher/importGbat10",
    "path_params": [],
    "query_params": []
  },
  "ledger_voucher_non_posted_non_posted": {
    "method": "GET",
    "path": "/ledger/voucher/>nonPosted",
    "path_params": [],
    "query_params": [
      "dateFrom",
      "dateTo",
      "includeNonApproved",
      "changedSince",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "ledger_voucher_options_options": {
    "method": "GET",
    "path": "/ledger/voucher/{id}/options",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "ledger_voucher_search": {
    "method": "GET",
    "path": "/ledger/voucher",
    "path_params": [],
    "query_params": [
      "id",
      "number",
      "numberFrom",
      "numberTo",
      "typeId",
      "dateFrom",
      "dateTo",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "ledger_voucher_post": {
    "method": "POST",
    "path": "/ledger/voucher",
    "path_params": [],
    "query_params": [
      "sendToLedger"
    ]
  },
  "ledger_voucher_list_put_list": {
    "method": "PUT",
    "path": "/ledger/voucher/list",
    "path_params": [],
    "query_params": [
      "sendToLedger"
    ]
  },
  "ledger_voucher_reverse_reverse": {
    "method": "PUT",
    "path": "/ledger/voucher/{id}/:reverse",
    "path_params": [
      "id"
    ],
    "query_params": [
      "date"
    ]
  },
  "ledger_voucher_send_to_inbox_send_to_inbox": {
    "method": "PUT",
    "path": "/ledger/voucher/{id}/:sendToInbox",
    "path_params": [
      "id"
    ],
    "query_params": [
      "version",
      "comment"
    ]
  },
  "ledger_voucher_send_to_ledger_send_to_ledger": {
    "method": "PUT",
    "path": "/ledger/voucher/{id}/:sendToLedger",
    "path_params": [
      "id"
    ],
    "query_params": [
      "version",
      "number"
    ]
  },
  "ledger_voucher_pdf_upload_pdf": {
    "method": "POST",
    "path": "/ledger/voucher/{voucherId}/pdf/{fileName}",
    "path_params": [
      "voucherId",
      "fileName"
    ],
    "query_params": []
  },
  "ledger_voucher_voucher_reception_voucher_reception": {
    "method": "GET",
    "path": "/ledger/voucher/>voucherReception",
    "path_params": [],
    "query_params": [
      "dateFrom",
      "dateTo",
      "searchText",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "municipality_query_query": {
    "method": "GET",
    "path": "/municipality/query",
    "path_params": [],
    "query_params": [
      "id",
      "query",
      "fields",
      "count",
      "from",
      "sorting"
    ]
  },
  "municipality_search": {
    "method": "GET",
    "path": "/municipality",
    "path_params": [],
    "query_params": [
      "includePayrollTaxZones",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "order_approve_subscription_invoice_approve_subscription_invoice": {
    "method": "PUT",
    "path": "/order/{id}/:approveSubscriptionInvoice",
    "path_params": [
      "id"
    ],
    "query_params": [
      "invoiceDate"
    ]
  },
  "order_attach_attach": {
    "method": "PUT",
    "path": "/order/{id}/:attach",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "order_get": {
    "method": "GET",
    "path": "/order/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "order_put": {
    "method": "PUT",
    "path": "/order/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "updateLinesAndGroups"
    ]
  },
  "order_delete": {
    "method": "DELETE",
    "path": "/order/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "order_packing_note_pdf_download_packing_note_pdf": {
    "method": "GET",
    "path": "/order/packingNote/{orderId}/pdf",
    "path_params": [
      "orderId"
    ],
    "query_params": [
      "type",
      "download"
    ]
  },
  "order_order_confirmation_pdf_download_pdf": {
    "method": "GET",
    "path": "/order/orderConfirmation/{orderId}/pdf",
    "path_params": [
      "orderId"
    ],
    "query_params": [
      "download"
    ]
  },
  "order_invoice_invoice": {
    "method": "PUT",
    "path": "/order/{id}/:invoice",
    "path_params": [
      "id"
    ],
    "query_params": [
      "invoiceDate",
      "sendToCustomer",
      "sendType",
      "paymentTypeId",
      "paidAmount",
      "paidAmountAccountCurrency",
      "paymentTypeIdRestAmount",
      "paidAmountAccountCurrencyRest",
      "createOnAccount",
      "amountOnAccount",
      "onAccountComment",
      "createBackorder",
      "invoiceIdIfIsCreditNote",
      "overrideEmailAddress"
    ]
  },
  "order_invoice_multiple_orders_invoice_multiple_orders": {
    "method": "PUT",
    "path": "/order/:invoiceMultipleOrders",
    "path_params": [],
    "query_params": [
      "id",
      "invoiceDate",
      "sendToCustomer",
      "createBackorders"
    ]
  },
  "order_search": {
    "method": "GET",
    "path": "/order",
    "path_params": [],
    "query_params": [
      "id",
      "number",
      "customerId",
      "orderDateFrom",
      "orderDateTo",
      "deliveryComment",
      "isClosed",
      "isSubscription",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "order_post": {
    "method": "POST",
    "path": "/order",
    "path_params": [],
    "query_params": []
  },
  "order_send_invoice_preview_post_invoice_preview": {
    "method": "PUT",
    "path": "/order/sendInvoicePreview/{orderId}",
    "path_params": [
      "orderId"
    ],
    "query_params": [
      "email",
      "message",
      "saveAsDefault"
    ]
  },
  "order_list_post_list": {
    "method": "POST",
    "path": "/order/list",
    "path_params": [],
    "query_params": []
  },
  "order_send_order_confirmation_post_order_confirmation": {
    "method": "PUT",
    "path": "/order/sendOrderConfirmation/{orderId}",
    "path_params": [
      "orderId"
    ],
    "query_params": [
      "email",
      "message",
      "saveAsDefault"
    ]
  },
  "order_send_packing_note_post_packing_note": {
    "method": "PUT",
    "path": "/order/sendPackingNote/{orderId}",
    "path_params": [
      "orderId"
    ],
    "query_params": [
      "email",
      "message",
      "saveAsDefault",
      "type"
    ]
  },
  "order_un_approve_subscription_invoice_un_approve_subscription_invoice": {
    "method": "PUT",
    "path": "/order/{id}/:unApproveSubscriptionInvoice",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "order_orderline_get": {
    "method": "GET",
    "path": "/order/orderline/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "order_orderline_put": {
    "method": "PUT",
    "path": "/order/orderline/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "order_orderline_delete": {
    "method": "DELETE",
    "path": "/order/orderline/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "order_orderline_list_post_list": {
    "method": "POST",
    "path": "/order/orderline/list",
    "path_params": [],
    "query_params": []
  },
  "order_orderline_order_line_template_order_line_template": {
    "method": "GET",
    "path": "/order/orderline/orderLineTemplate",
    "path_params": [],
    "query_params": [
      "orderId",
      "productId",
      "fields"
    ]
  },
  "order_orderline_pick_line_pick_line": {
    "method": "PUT",
    "path": "/order/orderline/{id}/:pickLine",
    "path_params": [
      "id"
    ],
    "query_params": [
      "inventoryId",
      "inventoryLocationId",
      "pickDate"
    ]
  },
  "order_orderline_post": {
    "method": "POST",
    "path": "/order/orderline",
    "path_params": [],
    "query_params": []
  },
  "order_orderline_unpick_line_unpick_line": {
    "method": "PUT",
    "path": "/order/orderline/{id}/:unpickLine",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "product_get": {
    "method": "GET",
    "path": "/product/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "product_put": {
    "method": "PUT",
    "path": "/product/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "product_delete": {
    "method": "DELETE",
    "path": "/product/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "product_image_upload_image": {
    "method": "POST",
    "path": "/product/{id}/image",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "product_image_delete_image": {
    "method": "DELETE",
    "path": "/product/{id}/image",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "product_list_put_list": {
    "method": "PUT",
    "path": "/product/list",
    "path_params": [],
    "query_params": []
  },
  "product_list_post_list": {
    "method": "POST",
    "path": "/product/list",
    "path_params": [],
    "query_params": []
  },
  "product_search": {
    "method": "GET",
    "path": "/product",
    "path_params": [],
    "query_params": [
      "number",
      "ids",
      "productNumber",
      "name",
      "ean",
      "isInactive",
      "isStockItem",
      "isSupplierProduct",
      "supplierId",
      "currencyId",
      "vatTypeId",
      "productUnitId",
      "departmentId",
      "accountId",
      "costExcludingVatCurrencyFrom",
      "costExcludingVatCurrencyTo",
      "priceExcludingVatCurrencyFrom",
      "priceExcludingVatCurrencyTo",
      "priceIncludingVatCurrencyFrom",
      "priceIncludingVatCurrencyTo",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "product_post": {
    "method": "POST",
    "path": "/product",
    "path_params": [],
    "query_params": []
  },
  "product_unit_get": {
    "method": "GET",
    "path": "/product/unit/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "product_unit_put": {
    "method": "PUT",
    "path": "/product/unit/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "product_unit_delete": {
    "method": "DELETE",
    "path": "/product/unit/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "product_unit_search": {
    "method": "GET",
    "path": "/product/unit",
    "path_params": [],
    "query_params": [
      "id",
      "name",
      "nameShort",
      "commonCode",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "product_unit_post": {
    "method": "POST",
    "path": "/product/unit",
    "path_params": [],
    "query_params": []
  },
  "product_unit_list_put_list": {
    "method": "PUT",
    "path": "/product/unit/list",
    "path_params": [],
    "query_params": []
  },
  "product_unit_list_post_list": {
    "method": "POST",
    "path": "/product/unit/list",
    "path_params": [],
    "query_params": []
  },
  "product_unit_query_query": {
    "method": "GET",
    "path": "/product/unit/query",
    "path_params": [],
    "query_params": [
      "query",
      "count",
      "fields",
      "from",
      "sorting"
    ]
  },
  "project_get": {
    "method": "GET",
    "path": "/project/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "project_put": {
    "method": "PUT",
    "path": "/project/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "project_delete": {
    "method": "DELETE",
    "path": "/project/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "project_list_put_list": {
    "method": "PUT",
    "path": "/project/list",
    "path_params": [],
    "query_params": []
  },
  "project_list_post_list": {
    "method": "POST",
    "path": "/project/list",
    "path_params": [],
    "query_params": []
  },
  "project_list_delete_by_ids": {
    "method": "DELETE",
    "path": "/project/list",
    "path_params": [],
    "query_params": [
      "ids"
    ]
  },
  "project_search": {
    "method": "GET",
    "path": "/project",
    "path_params": [],
    "query_params": [
      "id",
      "name",
      "number",
      "isOffer",
      "projectManagerId",
      "customerAccountManagerId",
      "employeeInProjectId",
      "departmentId",
      "startDateFrom",
      "startDateTo",
      "endDateFrom",
      "endDateTo",
      "isClosed",
      "isFixedPrice",
      "customerId",
      "externalAccountsNumber",
      "includeRecentlyClosed",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "project_post": {
    "method": "POST",
    "path": "/project",
    "path_params": [],
    "query_params": []
  },
  "project_delete_list": {
    "method": "DELETE",
    "path": "/project",
    "path_params": [],
    "query_params": []
  },
  "project_number_get_by_number": {
    "method": "GET",
    "path": "/project/number/{number}",
    "path_params": [
      "number"
    ],
    "query_params": [
      "fields"
    ]
  },
  "project_for_time_sheet_get_for_time_sheet": {
    "method": "GET",
    "path": "/project/>forTimeSheet",
    "path_params": [],
    "query_params": [
      "includeProjectOffers",
      "employeeId",
      "date",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "project_import_import_project_statement": {
    "method": "POST",
    "path": "/project/import",
    "path_params": [],
    "query_params": [
      "fileFormat",
      "encoding",
      "delimiter",
      "ignoreFirstRow"
    ]
  },
  "project_orderline_get": {
    "method": "GET",
    "path": "/project/orderline/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "project_orderline_put": {
    "method": "PUT",
    "path": "/project/orderline/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "project_orderline_delete": {
    "method": "DELETE",
    "path": "/project/orderline/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "project_orderline_list_post_list": {
    "method": "POST",
    "path": "/project/orderline/list",
    "path_params": [],
    "query_params": []
  },
  "project_orderline_order_line_template_order_line_template": {
    "method": "GET",
    "path": "/project/orderline/orderLineTemplate",
    "path_params": [],
    "query_params": [
      "projectId",
      "productId",
      "fields"
    ]
  },
  "project_orderline_search": {
    "method": "GET",
    "path": "/project/orderline",
    "path_params": [],
    "query_params": [
      "projectId",
      "isBudget",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "project_orderline_post": {
    "method": "POST",
    "path": "/project/orderline",
    "path_params": [],
    "query_params": []
  },
  "project_orderline_query_query": {
    "method": "GET",
    "path": "/project/orderline/query",
    "path_params": [],
    "query_params": [
      "id",
      "projectId",
      "query",
      "isBudget",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "project_participant_list_post_list": {
    "method": "POST",
    "path": "/project/participant/list",
    "path_params": [],
    "query_params": []
  },
  "project_participant_list_delete_by_ids": {
    "method": "DELETE",
    "path": "/project/participant/list",
    "path_params": [],
    "query_params": [
      "ids"
    ]
  },
  "project_participant_get": {
    "method": "GET",
    "path": "/project/participant/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "project_participant_put": {
    "method": "PUT",
    "path": "/project/participant/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "project_participant_post": {
    "method": "POST",
    "path": "/project/participant",
    "path_params": [],
    "query_params": []
  },
  "project_hourly_rates_get": {
    "method": "GET",
    "path": "/project/hourlyRates/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "project_hourly_rates_put": {
    "method": "PUT",
    "path": "/project/hourlyRates/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "project_hourly_rates_delete": {
    "method": "DELETE",
    "path": "/project/hourlyRates/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "project_hourly_rates_list_put_list": {
    "method": "PUT",
    "path": "/project/hourlyRates/list",
    "path_params": [],
    "query_params": []
  },
  "project_hourly_rates_list_post_list": {
    "method": "POST",
    "path": "/project/hourlyRates/list",
    "path_params": [],
    "query_params": []
  },
  "project_hourly_rates_list_delete_by_ids": {
    "method": "DELETE",
    "path": "/project/hourlyRates/list",
    "path_params": [],
    "query_params": [
      "ids"
    ]
  },
  "project_hourly_rates_delete_by_project_ids_delete_by_project_ids": {
    "method": "DELETE",
    "path": "/project/hourlyRates/deleteByProjectIds",
    "path_params": [],
    "query_params": [
      "ids",
      "date"
    ]
  },
  "project_hourly_rates_search": {
    "method": "GET",
    "path": "/project/hourlyRates",
    "path_params": [],
    "query_params": [
      "id",
      "projectId",
      "type",
      "startDateFrom",
      "startDateTo",
      "showInProjectOrder",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "project_hourly_rates_post": {
    "method": "POST",
    "path": "/project/hourlyRates",
    "path_params": [],
    "query_params": []
  },
  "project_hourly_rates_update_or_add_hour_rates_update_or_add_hour_rates": {
    "method": "PUT",
    "path": "/project/hourlyRates/updateOrAddHourRates",
    "path_params": [],
    "query_params": [
      "ids"
    ]
  },
  "project_hourly_rates_project_specific_rates_get": {
    "method": "GET",
    "path": "/project/hourlyRates/projectSpecificRates/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "project_hourly_rates_project_specific_rates_put": {
    "method": "PUT",
    "path": "/project/hourlyRates/projectSpecificRates/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "project_hourly_rates_project_specific_rates_delete": {
    "method": "DELETE",
    "path": "/project/hourlyRates/projectSpecificRates/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "project_hourly_rates_project_specific_rates_list_put_list": {
    "method": "PUT",
    "path": "/project/hourlyRates/projectSpecificRates/list",
    "path_params": [],
    "query_params": []
  },
  "project_hourly_rates_project_specific_rates_list_post_list": {
    "method": "POST",
    "path": "/project/hourlyRates/projectSpecificRates/list",
    "path_params": [],
    "query_params": []
  },
  "project_hourly_rates_project_specific_rates_list_delete_by_ids": {
    "method": "DELETE",
    "path": "/project/hourlyRates/projectSpecificRates/list",
    "path_params": [],
    "query_params": [
      "ids"
    ]
  },
  "project_hourly_rates_project_specific_rates_search": {
    "method": "GET",
    "path": "/project/hourlyRates/projectSpecificRates",
    "path_params": [],
    "query_params": [
      "id",
      "projectHourlyRateId",
      "employeeId",
      "activityId",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "project_hourly_rates_project_specific_rates_post": {
    "method": "POST",
    "path": "/project/hourlyRates/projectSpecificRates",
    "path_params": [],
    "query_params": []
  },
  "purchase_order_get": {
    "method": "GET",
    "path": "/purchaseOrder/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "purchase_order_put": {
    "method": "PUT",
    "path": "/purchaseOrder/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "purchase_order_delete": {
    "method": "DELETE",
    "path": "/purchaseOrder/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "purchase_order_attachment_upload_attachment": {
    "method": "POST",
    "path": "/purchaseOrder/{id}/attachment",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "purchase_order_attachment_delete_attachment": {
    "method": "DELETE",
    "path": "/purchaseOrder/{id}/attachment",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "purchase_order_search": {
    "method": "GET",
    "path": "/purchaseOrder",
    "path_params": [],
    "query_params": [
      "number",
      "deliveryDateFrom",
      "deliveryDateTo",
      "creationDateFrom",
      "creationDateTo",
      "id",
      "supplierId",
      "projectId",
      "isClosed",
      "withDeviationOnly",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "purchase_order_post": {
    "method": "POST",
    "path": "/purchaseOrder",
    "path_params": [],
    "query_params": []
  },
  "purchase_order_send_send": {
    "method": "PUT",
    "path": "/purchaseOrder/{id}/:send",
    "path_params": [
      "id"
    ],
    "query_params": [
      "sendType"
    ]
  },
  "purchase_order_send_by_email_send_by_email": {
    "method": "PUT",
    "path": "/purchaseOrder/{id}/:sendByEmail",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "purchase_order_attachment_list_upload_attachments": {
    "method": "POST",
    "path": "/purchaseOrder/{id}/attachment/list",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "purchase_order_orderline_get": {
    "method": "GET",
    "path": "/purchaseOrder/orderline/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "purchase_order_orderline_put": {
    "method": "PUT",
    "path": "/purchaseOrder/orderline/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "purchase_order_orderline_delete": {
    "method": "DELETE",
    "path": "/purchaseOrder/orderline/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "purchase_order_orderline_list_put_list": {
    "method": "PUT",
    "path": "/purchaseOrder/orderline/list",
    "path_params": [],
    "query_params": []
  },
  "purchase_order_orderline_list_post_list": {
    "method": "POST",
    "path": "/purchaseOrder/orderline/list",
    "path_params": [],
    "query_params": []
  },
  "purchase_order_orderline_list_delete_list": {
    "method": "DELETE",
    "path": "/purchaseOrder/orderline/list",
    "path_params": [],
    "query_params": []
  },
  "purchase_order_orderline_post": {
    "method": "POST",
    "path": "/purchaseOrder/orderline",
    "path_params": [],
    "query_params": []
  },
  "salary_type_get": {
    "method": "GET",
    "path": "/salary/type/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "salary_type_search": {
    "method": "GET",
    "path": "/salary/type",
    "path_params": [],
    "query_params": [
      "id",
      "number",
      "name",
      "description",
      "showInTimesheet",
      "isInactive",
      "employeeIds",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "supplier_get": {
    "method": "GET",
    "path": "/supplier/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "supplier_put": {
    "method": "PUT",
    "path": "/supplier/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "supplier_delete": {
    "method": "DELETE",
    "path": "/supplier/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "supplier_search": {
    "method": "GET",
    "path": "/supplier",
    "path_params": [],
    "query_params": [
      "id",
      "supplierNumber",
      "organizationNumber",
      "email",
      "invoiceEmail",
      "isInactive",
      "accountManagerId",
      "changedSince",
      "isWholesaler",
      "showProducts",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "supplier_post": {
    "method": "POST",
    "path": "/supplier",
    "path_params": [],
    "query_params": []
  },
  "supplier_list_put_list": {
    "method": "PUT",
    "path": "/supplier/list",
    "path_params": [],
    "query_params": []
  },
  "supplier_list_post_list": {
    "method": "POST",
    "path": "/supplier/list",
    "path_params": [],
    "query_params": []
  },
  "supplier_invoice_add_payment_add_payment": {
    "method": "POST",
    "path": "/supplierInvoice/{invoiceId}/:addPayment",
    "path_params": [
      "invoiceId"
    ],
    "query_params": [
      "paymentType",
      "amount",
      "kidOrReceiverReference",
      "bban",
      "paymentDate",
      "useDefaultPaymentType",
      "partialPayment"
    ]
  },
  "supplier_invoice_add_recipient_add_recipient": {
    "method": "PUT",
    "path": "/supplierInvoice/{invoiceId}/:addRecipient",
    "path_params": [
      "invoiceId"
    ],
    "query_params": [
      "employeeId",
      "comment"
    ]
  },
  "supplier_invoice_add_recipient_add_recipient_to_many": {
    "method": "PUT",
    "path": "/supplierInvoice/:addRecipient",
    "path_params": [],
    "query_params": [
      "employeeId",
      "invoiceIds",
      "comment"
    ]
  },
  "supplier_invoice_approve_approve": {
    "method": "PUT",
    "path": "/supplierInvoice/{invoiceId}/:approve",
    "path_params": [
      "invoiceId"
    ],
    "query_params": [
      "comment"
    ]
  },
  "supplier_invoice_approve_approve_many": {
    "method": "PUT",
    "path": "/supplierInvoice/:approve",
    "path_params": [],
    "query_params": [
      "invoiceIds",
      "comment"
    ]
  },
  "supplier_invoice_change_dimension_change_dimension_many": {
    "method": "PUT",
    "path": "/supplierInvoice/{invoiceId}/:changeDimension",
    "path_params": [
      "invoiceId"
    ],
    "query_params": [
      "debitPostingIds",
      "dimension",
      "dimensionId"
    ]
  },
  "supplier_invoice_pdf_download_pdf": {
    "method": "GET",
    "path": "/supplierInvoice/{invoiceId}/pdf",
    "path_params": [
      "invoiceId"
    ],
    "query_params": []
  },
  "supplier_invoice_get": {
    "method": "GET",
    "path": "/supplierInvoice/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "supplier_invoice_for_approval_get_approval_invoices": {
    "method": "GET",
    "path": "/supplierInvoice/forApproval",
    "path_params": [],
    "query_params": [
      "searchText",
      "showAll",
      "employeeId",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "supplier_invoice_search": {
    "method": "GET",
    "path": "/supplierInvoice",
    "path_params": [],
    "query_params": [
      "id",
      "invoiceDateFrom",
      "invoiceDateTo",
      "invoiceNumber",
      "kid",
      "voucherId",
      "supplierId",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "supplier_invoice_voucher_postings_put_postings": {
    "method": "PUT",
    "path": "/supplierInvoice/voucher/{id}/postings",
    "path_params": [
      "id"
    ],
    "query_params": [
      "sendToLedger",
      "voucherDate"
    ]
  },
  "supplier_invoice_reject_reject": {
    "method": "PUT",
    "path": "/supplierInvoice/{invoiceId}/:reject",
    "path_params": [
      "invoiceId"
    ],
    "query_params": [
      "comment"
    ]
  },
  "supplier_invoice_reject_reject_many": {
    "method": "PUT",
    "path": "/supplierInvoice/:reject",
    "path_params": [],
    "query_params": [
      "comment",
      "invoiceIds"
    ]
  },
  "timesheet_entry_get": {
    "method": "GET",
    "path": "/timesheet/entry/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "timesheet_entry_put": {
    "method": "PUT",
    "path": "/timesheet/entry/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "timesheet_entry_delete": {
    "method": "DELETE",
    "path": "/timesheet/entry/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "version"
    ]
  },
  "timesheet_entry_list_put_list": {
    "method": "PUT",
    "path": "/timesheet/entry/list",
    "path_params": [],
    "query_params": []
  },
  "timesheet_entry_list_post_list": {
    "method": "POST",
    "path": "/timesheet/entry/list",
    "path_params": [],
    "query_params": []
  },
  "timesheet_entry_search": {
    "method": "GET",
    "path": "/timesheet/entry",
    "path_params": [],
    "query_params": [
      "id",
      "employeeId",
      "projectId",
      "activityId",
      "dateFrom",
      "dateTo",
      "comment",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "timesheet_entry_post": {
    "method": "POST",
    "path": "/timesheet/entry",
    "path_params": [],
    "query_params": []
  },
  "timesheet_entry_recent_activities_get_recent_activities": {
    "method": "GET",
    "path": "/timesheet/entry/>recentActivities",
    "path_params": [],
    "query_params": [
      "employeeId",
      "projectId",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "timesheet_entry_recent_projects_get_recent_projects": {
    "method": "GET",
    "path": "/timesheet/entry/>recentProjects",
    "path_params": [],
    "query_params": [
      "employeeId",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "timesheet_entry_total_hours_get_total_hours": {
    "method": "GET",
    "path": "/timesheet/entry/>totalHours",
    "path_params": [],
    "query_params": [
      "employeeId",
      "startDate",
      "endDate",
      "fields"
    ]
  },
  "travel_expense_accommodation_allowance_get": {
    "method": "GET",
    "path": "/travelExpense/accommodationAllowance/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "travel_expense_accommodation_allowance_put": {
    "method": "PUT",
    "path": "/travelExpense/accommodationAllowance/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "travel_expense_accommodation_allowance_delete": {
    "method": "DELETE",
    "path": "/travelExpense/accommodationAllowance/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "travel_expense_accommodation_allowance_search": {
    "method": "GET",
    "path": "/travelExpense/accommodationAllowance",
    "path_params": [],
    "query_params": [
      "travelExpenseId",
      "rateTypeId",
      "rateCategoryId",
      "rateFrom",
      "rateTo",
      "countFrom",
      "countTo",
      "amountFrom",
      "amountTo",
      "location",
      "address",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "travel_expense_accommodation_allowance_post": {
    "method": "POST",
    "path": "/travelExpense/accommodationAllowance",
    "path_params": [],
    "query_params": []
  },
  "travel_expense_cost_get": {
    "method": "GET",
    "path": "/travelExpense/cost/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "travel_expense_cost_put": {
    "method": "PUT",
    "path": "/travelExpense/cost/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "travel_expense_cost_delete": {
    "method": "DELETE",
    "path": "/travelExpense/cost/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "travel_expense_cost_search": {
    "method": "GET",
    "path": "/travelExpense/cost",
    "path_params": [],
    "query_params": [
      "travelExpenseId",
      "vatTypeId",
      "currencyId",
      "rateFrom",
      "rateTo",
      "countFrom",
      "countTo",
      "amountFrom",
      "amountTo",
      "location",
      "address",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "travel_expense_cost_post": {
    "method": "POST",
    "path": "/travelExpense/cost",
    "path_params": [],
    "query_params": []
  },
  "travel_expense_cost_list_put_list": {
    "method": "PUT",
    "path": "/travelExpense/cost/list",
    "path_params": [],
    "query_params": []
  },
  "travel_expense_mileage_allowance_get": {
    "method": "GET",
    "path": "/travelExpense/mileageAllowance/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "travel_expense_mileage_allowance_put": {
    "method": "PUT",
    "path": "/travelExpense/mileageAllowance/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "travel_expense_mileage_allowance_delete": {
    "method": "DELETE",
    "path": "/travelExpense/mileageAllowance/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "travel_expense_mileage_allowance_search": {
    "method": "GET",
    "path": "/travelExpense/mileageAllowance",
    "path_params": [],
    "query_params": [
      "travelExpenseId",
      "rateTypeId",
      "rateCategoryId",
      "kmFrom",
      "kmTo",
      "rateFrom",
      "rateTo",
      "amountFrom",
      "amountTo",
      "departureLocation",
      "destination",
      "dateFrom",
      "dateTo",
      "isCompanyCar",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "travel_expense_mileage_allowance_post": {
    "method": "POST",
    "path": "/travelExpense/mileageAllowance",
    "path_params": [],
    "query_params": []
  },
  "travel_expense_per_diem_compensation_get": {
    "method": "GET",
    "path": "/travelExpense/perDiemCompensation/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "travel_expense_per_diem_compensation_put": {
    "method": "PUT",
    "path": "/travelExpense/perDiemCompensation/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "travel_expense_per_diem_compensation_delete": {
    "method": "DELETE",
    "path": "/travelExpense/perDiemCompensation/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "travel_expense_per_diem_compensation_search": {
    "method": "GET",
    "path": "/travelExpense/perDiemCompensation",
    "path_params": [],
    "query_params": [
      "travelExpenseId",
      "rateTypeId",
      "rateCategoryId",
      "overnightAccommodation",
      "countFrom",
      "countTo",
      "rateFrom",
      "rateTo",
      "amountFrom",
      "amountTo",
      "location",
      "address",
      "isDeductionForBreakfast",
      "isLunchDeduction",
      "isDinnerDeduction",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "travel_expense_per_diem_compensation_post": {
    "method": "POST",
    "path": "/travelExpense/perDiemCompensation",
    "path_params": [],
    "query_params": []
  },
  "travel_expense_approve_approve": {
    "method": "PUT",
    "path": "/travelExpense/:approve",
    "path_params": [],
    "query_params": [
      "id",
      "overrideApprovalFlow"
    ]
  },
  "travel_expense_convert_convert": {
    "method": "PUT",
    "path": "/travelExpense/{id}/convert",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "travel_expense_copy_copy": {
    "method": "PUT",
    "path": "/travelExpense/:copy",
    "path_params": [],
    "query_params": [
      "id"
    ]
  },
  "travel_expense_create_vouchers_create_vouchers": {
    "method": "PUT",
    "path": "/travelExpense/:createVouchers",
    "path_params": [],
    "query_params": [
      "id",
      "date"
    ]
  },
  "travel_expense_get": {
    "method": "GET",
    "path": "/travelExpense/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "travel_expense_put": {
    "method": "PUT",
    "path": "/travelExpense/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "travel_expense_delete": {
    "method": "DELETE",
    "path": "/travelExpense/{id}",
    "path_params": [
      "id"
    ],
    "query_params": []
  },
  "travel_expense_attachment_download_attachment": {
    "method": "GET",
    "path": "/travelExpense/{travelExpenseId}/attachment",
    "path_params": [
      "travelExpenseId"
    ],
    "query_params": []
  },
  "travel_expense_attachment_upload_attachment": {
    "method": "POST",
    "path": "/travelExpense/{travelExpenseId}/attachment",
    "path_params": [
      "travelExpenseId"
    ],
    "query_params": [
      "createNewCost"
    ]
  },
  "travel_expense_attachment_delete_attachment": {
    "method": "DELETE",
    "path": "/travelExpense/{travelExpenseId}/attachment",
    "path_params": [
      "travelExpenseId"
    ],
    "query_params": [
      "version",
      "sendToInbox",
      "split"
    ]
  },
  "travel_expense_deliver_deliver": {
    "method": "PUT",
    "path": "/travelExpense/:deliver",
    "path_params": [],
    "query_params": [
      "id"
    ]
  },
  "travel_expense_search": {
    "method": "GET",
    "path": "/travelExpense",
    "path_params": [],
    "query_params": [
      "employeeId",
      "departmentId",
      "projectId",
      "projectManagerId",
      "departureDateFrom",
      "returnDateTo",
      "state",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "travel_expense_post": {
    "method": "POST",
    "path": "/travelExpense",
    "path_params": [],
    "query_params": []
  },
  "travel_expense_unapprove_unapprove": {
    "method": "PUT",
    "path": "/travelExpense/:unapprove",
    "path_params": [],
    "query_params": [
      "id"
    ]
  },
  "travel_expense_undeliver_undeliver": {
    "method": "PUT",
    "path": "/travelExpense/:undeliver",
    "path_params": [],
    "query_params": [
      "id"
    ]
  },
  "travel_expense_attachment_list_upload_attachments": {
    "method": "POST",
    "path": "/travelExpense/{travelExpenseId}/attachment/list",
    "path_params": [
      "travelExpenseId"
    ],
    "query_params": [
      "createNewCost"
    ]
  },
  "travel_expense_rate_get": {
    "method": "GET",
    "path": "/travelExpense/rate/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "travel_expense_rate_search": {
    "method": "GET",
    "path": "/travelExpense/rate",
    "path_params": [],
    "query_params": [
      "rateCategoryId",
      "type",
      "isValidDayTrip",
      "isValidAccommodation",
      "isValidDomestic",
      "isValidForeignTravel",
      "requiresZone",
      "requiresOvernightAccommodation",
      "dateFrom",
      "dateTo",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "travel_expense_rate_category_get": {
    "method": "GET",
    "path": "/travelExpense/rateCategory/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "travel_expense_rate_category_search": {
    "method": "GET",
    "path": "/travelExpense/rateCategory",
    "path_params": [],
    "query_params": [
      "type",
      "name",
      "travelReportRateCategoryGroupId",
      "ameldingWageCode",
      "wageCodeNumber",
      "isValidDayTrip",
      "isValidAccommodation",
      "isValidDomestic",
      "requiresZone",
      "isRequiresOvernightAccommodation",
      "dateFrom",
      "dateTo",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "travel_expense_cost_category_get": {
    "method": "GET",
    "path": "/travelExpense/costCategory/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "travel_expense_cost_category_search": {
    "method": "GET",
    "path": "/travelExpense/costCategory",
    "path_params": [],
    "query_params": [
      "id",
      "description",
      "isInactive",
      "showOnEmployeeExpenses",
      "query",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  },
  "travel_expense_payment_type_get": {
    "method": "GET",
    "path": "/travelExpense/paymentType/{id}",
    "path_params": [
      "id"
    ],
    "query_params": [
      "fields"
    ]
  },
  "travel_expense_payment_type_search": {
    "method": "GET",
    "path": "/travelExpense/paymentType",
    "path_params": [],
    "query_params": [
      "id",
      "description",
      "isInactive",
      "showOnEmployeeExpenses",
      "query",
      "from",
      "count",
      "sorting",
      "fields"
    ]
  }
}
