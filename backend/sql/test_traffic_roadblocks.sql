-- ============================================================
-- SQL Script: Test Data for Roadblocks and Traffic Updates
-- ============================================================
-- Purpose: Insert test data to verify the routing engine correctly
--          handles traffic delays and roadblocks when computing
--          ambulance routes and ETAs.
--
-- How the system uses this data:
-- 1. build_graph_for_city() loads nodes and edges into memory
-- 2. apply_dynamic_traffic() modifies the graph:
--    - ROADBLOCKS: Removes edges entirely (road is blocked)
--    - TRAFFIC_UPDATES: Modifies edge weights (increased travel time)
-- 3. Dijkstra's algorithm finds shortest path using modified weights
-- ============================================================

-- First, clear existing test data (optional - uncomment if needed)
-- DELETE FROM roadblocks;
-- DELETE FROM traffic_updates;

-- ============================================================
-- TRAFFIC UPDATES
-- ============================================================
-- These increase the travel time (weight) on specific edges
-- to simulate heavy traffic conditions.
--
-- Effect: Ambulances will avoid these routes if faster alternatives exist
-- ============================================================

-- CITY 1 (Nodes 7-13): Heavy traffic on main routes from hub (node 7)
-- Edge 13: 7 -> 8, original weight 5, now 15 (3x slower due to traffic)
INSERT INTO traffic_updates (edge_id, new_weight, timestamp) 
VALUES (13, 15.0, CURRENT_TIMESTAMP);

-- Edge 14: 8 -> 7, original weight 5, now 15 (bidirectional traffic)
INSERT INTO traffic_updates (edge_id, new_weight, timestamp) 
VALUES (14, 15.0, CURRENT_TIMESTAMP);

-- CITY 2 (Nodes 14-20): Moderate traffic on some routes
-- Edge 29: 14 -> 15, original weight 5, now 10 (2x slower)
INSERT INTO traffic_updates (edge_id, new_weight, timestamp) 
VALUES (29, 10.0, CURRENT_TIMESTAMP);

-- Edge 30: 15 -> 14, original weight 5, now 10 (bidirectional)
INSERT INTO traffic_updates (edge_id, new_weight, timestamp) 
VALUES (30, 10.0, CURRENT_TIMESTAMP);

-- CITY 3 (Nodes 21-27): Rush hour traffic simulation
-- Edge 45: 21 -> 22, original weight 5, now 12
INSERT INTO traffic_updates (edge_id, new_weight, timestamp) 
VALUES (45, 12.0, CURRENT_TIMESTAMP);

-- Edge 46: 22 -> 21, original weight 5, now 12
INSERT INTO traffic_updates (edge_id, new_weight, timestamp) 
VALUES (46, 12.0, CURRENT_TIMESTAMP);

-- Edge 57: 26 -> 22, original weight 3, now 8 (alternate route also congested)
INSERT INTO traffic_updates (edge_id, new_weight, timestamp) 
VALUES (57, 8.0, CURRENT_TIMESTAMP);

-- CITY 4 (Nodes 28-34): Light traffic increase
-- Edge 61: 28 -> 29, original weight 5, now 7
INSERT INTO traffic_updates (edge_id, new_weight, timestamp) 
VALUES (61, 7.0, CURRENT_TIMESTAMP);

-- Edge 62: 29 -> 28, original weight 5, now 7
INSERT INTO traffic_updates (edge_id, new_weight, timestamp) 
VALUES (62, 7.0, CURRENT_TIMESTAMP);

-- CITY 5 (Nodes 35-41): Severe traffic on main road
-- Edge 77: 35 -> 36, original weight 5, now 20 (4x slower - accident ahead)
INSERT INTO traffic_updates (edge_id, new_weight, timestamp) 
VALUES (77, 20.0, CURRENT_TIMESTAMP);

-- Edge 78: 36 -> 35, original weight 5, now 20
INSERT INTO traffic_updates (edge_id, new_weight, timestamp) 
VALUES (78, 20.0, CURRENT_TIMESTAMP);


-- ============================================================
-- ROADBLOCKS
-- ============================================================
-- These completely block edges - the routing engine will
-- remove these edges from the graph entirely.
--
-- Effect: Ambulances CANNOT use these routes at all
-- ============================================================

-- CITY 1: Road construction blocking route 7 -> 9
-- Edge 15: 7 -> 9 is BLOCKED
INSERT INTO roadblocks (edge_id, start_time, end_time, reason) 
VALUES (15, CURRENT_TIMESTAMP, NULL, 'Road construction - estimated 2 days');

-- Edge 16: 9 -> 7 is also BLOCKED (bidirectional closure)
INSERT INTO roadblocks (edge_id, start_time, end_time, reason) 
VALUES (16, CURRENT_TIMESTAMP, NULL, 'Road construction - estimated 2 days');

-- CITY 2: Accident blocking route 14 -> 17
-- Edge 33: 14 -> 17 is BLOCKED
INSERT INTO roadblocks (edge_id, start_time, end_time, reason) 
VALUES (33, CURRENT_TIMESTAMP, NULL, 'Traffic accident - clearing in progress');

-- Edge 34: 17 -> 14 is also BLOCKED
INSERT INTO roadblocks (edge_id, start_time, end_time, reason) 
VALUES (34, CURRENT_TIMESTAMP, NULL, 'Traffic accident - clearing in progress');

-- CITY 3: Flooding blocking route 21 -> 24
-- Edge 49: 21 -> 24 is BLOCKED
INSERT INTO roadblocks (edge_id, start_time, end_time, reason) 
VALUES (49, CURRENT_TIMESTAMP, NULL, 'Flooding - road submerged');

-- Edge 50: 24 -> 21 is also BLOCKED
INSERT INTO roadblocks (edge_id, start_time, end_time, reason) 
VALUES (50, CURRENT_TIMESTAMP, NULL, 'Flooding - road submerged');

-- CITY 4: VIP movement blocking route 28 -> 31
-- Edge 65: 28 -> 31 is BLOCKED
INSERT INTO roadblocks (edge_id, start_time, end_time, reason) 
VALUES (65, NOW(), DATE_ADD(NOW(), INTERVAL 2 HOUR), 'VIP movement - temporary closure');

-- Edge 66: 31 -> 28 is also BLOCKED
INSERT INTO roadblocks (edge_id, start_time, end_time, reason) 
VALUES (66, NOW(), DATE_ADD(NOW(), INTERVAL 2 HOUR), 'VIP movement - temporary closure');

-- CITY 5: Gas leak blocking route 35 -> 38
-- Edge 81: 35 -> 38 is BLOCKED
INSERT INTO roadblocks (edge_id, start_time, end_time, reason) 
VALUES (81, CURRENT_TIMESTAMP, NULL, 'Gas leak - emergency evacuation zone');

-- Edge 82: 38 -> 35 is also BLOCKED
INSERT INTO roadblocks (edge_id, start_time, end_time, reason) 
VALUES (82, CURRENT_TIMESTAMP, NULL, 'Gas leak - emergency evacuation zone');


-- ============================================================
-- VERIFICATION QUERIES
-- ============================================================
-- Run these to verify the data was inserted correctly

-- Check traffic updates
SELECT 
    tu.id,
    tu.edge_id,
    e.from_node,
    e.to_node,
    e.weight AS original_weight,
    tu.new_weight AS traffic_adjusted_weight,
    tu.timestamp
FROM traffic_updates tu
JOIN edges e ON tu.edge_id = e.id
ORDER BY tu.edge_id;

-- Check roadblocks
SELECT 
    rb.id,
    rb.edge_id,
    e.from_node,
    e.to_node,
    rb.reason,
    rb.start_time,
    rb.end_time
FROM roadblocks rb
JOIN edges e ON rb.edge_id = e.id
ORDER BY rb.edge_id;

-- ============================================================
-- TEST SCENARIOS
-- ============================================================
-- After inserting this data, test the routing with these scenarios:
--
-- SCENARIO 1 (City 1): 
--   - Route 7->9 is BLOCKED (roadblock)
--   - Route 7->8 has HEAVY TRAFFIC (weight 5 -> 15)
--   - Ambulance should prefer routes through nodes 10,11,12,13
--
-- SCENARIO 2 (City 2):
--   - Route 14->17 is BLOCKED (roadblock)
--   - Route 14->15 has MODERATE TRAFFIC (weight 5 -> 10)
--   - Ambulance should use 14->16, 14->18, 14->19, or 14->20
--
-- SCENARIO 3 (City 3):
--   - Route 21->24 is BLOCKED (flooding)
--   - Route 21->22 has TRAFFIC (weight 5 -> 12)
--   - Route 26->22 also congested (weight 3 -> 8)
--   - Tests multiple constraints affecting route choice
--
-- SCENARIO 4 (City 4):
--   - Route 28->31 is temporarily BLOCKED (VIP movement)
--   - Route 28->29 has LIGHT TRAFFIC (weight 5 -> 7)
--   - Should still find optimal routes
--
-- SCENARIO 5 (City 5):
--   - Route 35->38 is BLOCKED (gas leak)
--   - Route 35->36 has SEVERE TRAFFIC (weight 5 -> 20)
--   - Forces ambulance to use routes through 37,39,40,41
-- ============================================================

