PRAGMA foreign_keys = ON;

CREATE TABLE locations (
  location_id TEXT PRIMARY KEY, original_store_id TEXT NOT NULL UNIQUE,
  region TEXT NOT NULL, location_name TEXT NOT NULL
);
CREATE TABLE local_skus (
  local_sku_id TEXT PRIMARY KEY, original_product_id TEXT NOT NULL,
  location_id TEXT NOT NULL REFERENCES locations(location_id), category TEXT NOT NULL,
  UNIQUE (location_id, original_product_id), UNIQUE (local_sku_id, location_id)
);
CREATE TABLE daily_operations (
  date TEXT NOT NULL CHECK(date = date(date)), inventory_units INTEGER NOT NULL CHECK(inventory_units >= 0),
  units_sold INTEGER NOT NULL CHECK(units_sold >= 0), units_ordered_source INTEGER NOT NULL CHECK(units_ordered_source >= 0),
  listed_price REAL NOT NULL CHECK(listed_price > 0), discount_source INTEGER NOT NULL CHECK(discount_source BETWEEN 0 AND 100),
  weather_condition TEXT NOT NULL, promotion_flag INTEGER NOT NULL CHECK(promotion_flag IN (0,1)),
  competitor_price REAL NOT NULL CHECK(competitor_price > 0), seasonality_label TEXT NOT NULL,
  epidemic_flag INTEGER NOT NULL CHECK(epidemic_flag IN (0,1)), estimated_demand_source INTEGER NOT NULL CHECK(estimated_demand_source >= 0),
  location_id TEXT NOT NULL, local_sku_id TEXT NOT NULL, year INTEGER NOT NULL, quarter INTEGER NOT NULL,
  month INTEGER NOT NULL, month_name TEXT NOT NULL, week_of_year INTEGER NOT NULL,
  day_of_week INTEGER NOT NULL, day_name TEXT NOT NULL, is_weekend INTEGER NOT NULL CHECK(is_weekend IN (0,1)),
  data_origin TEXT NOT NULL CHECK(data_origin = 'SOURCE_SYNTHETIC_PLUS_DERIVED'),
  PRIMARY KEY(date, local_sku_id),
  FOREIGN KEY(local_sku_id, location_id) REFERENCES local_skus(local_sku_id, location_id)
);
CREATE TABLE suppliers (
  supplier_id TEXT PRIMARY KEY, supplier_name TEXT NOT NULL, supplier_region TEXT NOT NULL,
  base_lead_time_days INTEGER NOT NULL CHECK(base_lead_time_days > 0),
  lead_time_variability_days REAL NOT NULL CHECK(lead_time_variability_days >= 0),
  unit_cost_factor REAL NOT NULL CHECK(unit_cost_factor > 0),
  fulfillment_probability_assumption REAL NOT NULL CHECK(fulfillment_probability_assumption BETWEEN 0 AND 1),
  data_origin TEXT NOT NULL CHECK(data_origin = 'SIMULATED')
);
CREATE TABLE sku_supplier_map (
  local_sku_id TEXT NOT NULL REFERENCES local_skus(local_sku_id),
  supplier_id TEXT NOT NULL REFERENCES suppliers(supplier_id),
  primary_supplier_flag INTEGER NOT NULL CHECK(primary_supplier_flag IN (0,1)),
  expected_lead_time_days INTEGER NOT NULL CHECK(expected_lead_time_days > 0),
  procurement_unit_cost REAL NOT NULL CHECK(procurement_unit_cost > 0),
  data_origin TEXT NOT NULL CHECK(data_origin = 'SIMULATED'),
  PRIMARY KEY(local_sku_id, supplier_id)
);
CREATE TABLE purchase_orders (
  po_id TEXT PRIMARY KEY, supplier_id TEXT NOT NULL, local_sku_id TEXT NOT NULL,
  location_id TEXT NOT NULL REFERENCES locations(location_id), order_date TEXT NOT NULL CHECK(order_date = date(order_date)),
  ordered_quantity INTEGER NOT NULL CHECK(ordered_quantity > 0),
  expected_delivery_date TEXT NOT NULL CHECK(expected_delivery_date = date(expected_delivery_date) AND expected_delivery_date >= order_date),
  procurement_unit_cost REAL NOT NULL CHECK(procurement_unit_cost > 0),
  po_status TEXT NOT NULL CHECK(po_status IN ('RECEIVED','PARTIALLY_RECEIVED')),
  data_origin TEXT NOT NULL CHECK(data_origin = 'SIMULATED'),
  FOREIGN KEY(local_sku_id, supplier_id) REFERENCES sku_supplier_map(local_sku_id, supplier_id),
  FOREIGN KEY(local_sku_id, location_id) REFERENCES local_skus(local_sku_id, location_id)
);
CREATE TABLE receipts (
  receipt_id TEXT PRIMARY KEY, po_id TEXT NOT NULL UNIQUE REFERENCES purchase_orders(po_id),
  actual_delivery_date TEXT NOT NULL CHECK(actual_delivery_date = date(actual_delivery_date)),
  received_quantity INTEGER NOT NULL CHECK(received_quantity >= 0),
  delivery_status TEXT NOT NULL CHECK(delivery_status IN ('COMPLETE','PARTIAL')),
  data_origin TEXT NOT NULL CHECK(data_origin = 'SIMULATED')
);

CREATE INDEX idx_daily_sku_date ON daily_operations(local_sku_id, date);
CREATE INDEX idx_daily_location_date ON daily_operations(location_id, date);
CREATE INDEX idx_po_supplier_date ON purchase_orders(supplier_id, order_date);
CREATE INDEX idx_po_location_date ON purchase_orders(location_id, order_date);
CREATE INDEX idx_receipt_actual_date ON receipts(actual_delivery_date);
