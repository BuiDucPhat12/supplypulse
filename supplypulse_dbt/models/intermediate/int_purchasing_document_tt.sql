WITH pd AS (
    SELECT * FROM {{ ref('int_purchasing_document_active') }}
),

tt AS (
    SELECT * FROM {{ ref('int_transit_time') }}
),

qa AS (
    -- Guard against multiple active quota arrangements per material+plant+vendor
    SELECT
        material_number,
        plant,
        vendor_number,
        MAX(quote_percent) AS quote_percent
    FROM {{ ref('int_valid_quote_agreements') }}
    GROUP BY material_number, plant, vendor_number
),

joined AS (
    SELECT
        pd.ekpo_id,
        pd.po_number,
        pd.vendor_number,
        pd.purchasing_org,
        pd.po_item,
        pd.marc_id,
        pd.material_number,
        pd.plant,
        pd.po_type,
        pd.po_date,
        pd.order_quantity,
        tt.transit_time_days,
        tt.factory_calendar_key,
        qa.quote_percent
    FROM pd
    LEFT JOIN tt
        ON  pd.vendor_number  = tt.vendor_number
        AND pd.plant          = tt.plant
        AND pd.purchasing_org = tt.purchasing_org
    LEFT JOIN qa
        ON  pd.material_number = qa.material_number
        AND pd.plant           = qa.plant
        AND pd.vendor_number   = qa.vendor_number
)

SELECT * FROM joined
