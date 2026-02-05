**KPI Definitions**
All KPIs are computed from `flight_fares_analytics` in Postgres for the latest `load_ts` batch and grouped by `flight_date` (stored as `kpi_date`).

**kpi_daily_avg_fare_by_airline**
- Description: Daily average total fare per airline for the latest load batch.
- Columns: `kpi_date` DATE, `load_ts` TIMESTAMP, `airline` TEXT, `avg_fare` NUMERIC(10, 2)
- Logic: `ROUND(AVG(total_fare)::numeric, 2)` grouped by `flight_date, airline`, filtered to latest `load_ts`.

**kpi_daily_booking_count_by_airline**
- Description: Daily booking count per airline for the latest load batch.
- Columns: `kpi_date` DATE, `load_ts` TIMESTAMP, `airline` TEXT, `booking_count` BIGINT
- Logic: `COUNT(*)` grouped by `flight_date, airline`, filtered to latest `load_ts`.

**kpi_daily_seasonal_fares**
- Description: Daily average total fare for peak vs non-peak season in the latest load batch.
- Columns: `kpi_date` DATE, `load_ts` TIMESTAMP, `season` TEXT, `avg_fare` NUMERIC(10, 2)
- Logic: `ROUND(AVG(total_fare)::numeric, 2)` grouped by `flight_date, season`, filtered to latest `load_ts`.

**kpi_daily_popular_routes**
- Description: Daily booking count by route in the latest load batch.
- Columns: `kpi_date` DATE, `load_ts` TIMESTAMP, `source` TEXT, `destination` TEXT, `booking_count` BIGINT
- Logic: `COUNT(*)` grouped by `flight_date, source, destination`, filtered to latest `load_ts`.
