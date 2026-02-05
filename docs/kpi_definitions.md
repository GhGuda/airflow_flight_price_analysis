**KPI Definitions**
All KPIs are computed from `flight_fares_analytics` in Postgres for the Airflow execution date (`kpi_date`).

**kpi_daily_avg_fare_by_airline**
- Description: Daily average total fare per airline.
- Columns: `kpi_date` DATE, `airline` TEXT, `avg_fare` NUMERIC(10, 2)
- Logic: `ROUND(AVG(total_fare)::numeric, 2)` grouped by `flight_date, airline`.

**kpi_daily_booking_count_by_airline**
- Description: Daily booking count per airline.
- Columns: `kpi_date` DATE, `airline` TEXT, `booking_count` BIGINT
- Logic: `COUNT(*)` grouped by `flight_date, airline`.

**kpi_daily_seasonal_fares**
- Description: Daily average total fare for peak vs non-peak season.
- Columns: `kpi_date` DATE, `season` TEXT, `avg_fare` NUMERIC(10, 2)
- Logic: `ROUND(AVG(total_fare)::numeric, 2)` grouped by `flight_date, season`.

**kpi_daily_popular_routes**
- Description: Daily booking count by route.
- Columns: `kpi_date` DATE, `source` TEXT, `destination` TEXT, `booking_count` BIGINT
- Logic: `COUNT(*)` grouped by `flight_date, source, destination`.
