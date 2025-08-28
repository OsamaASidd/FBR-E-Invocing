-- -- Initial provinces
-- INSERT IGNORE INTO provinces (name) VALUES 
-- ('Punjab'),
-- ('Sindh'),
-- ('Khyber Pakhtunkhwa'),
-- ('Balochistan'),
-- ('Gilgit-Baltistan'),
-- ('Azad Kashmir'),
-- ('Islamabad Capital Territory');

-- -- Sample HS Codes
-- INSERT IGNORE INTO hs_codes (code, description) VALUES 
-- ('1001', 'Wheat and meslin'),
-- ('1002', 'Rye'),
-- ('1003', 'Barley'),
-- ('1004', 'Oats'),
-- ('1005', 'Maize (corn)'),
-- ('8471', 'Automatic data processing machines'),
-- ('8542', 'Electronic integrated circuits'),
-- ('9999', 'General/Other');

-- -- Sample Company
-- INSERT IGNORE INTO companies (name, tax_id, province, address) VALUES 
-- ('Default Company', '1234567890', 'Punjab', 'Sample Address, Lahore');

-- -- Sample Customer
-- INSERT IGNORE INTO customers (name, tax_id, province, address) VALUES 
-- ('Default Customer', '0987654321', 'Punjab', 'Customer Address, Karachi');