CREATE TYPE property_data_type AS ENUM ('STRING', 'NUMBER', 'ENUM');

CREATE TABLE containers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL
);

CREATE TABLE properties (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    data_type property_data_type DEFAULT 'STRING'
);

CREATE TABLE property_options (
    id SERIAL PRIMARY KEY,
    property_id INT REFERENCES properties(id) ON DELETE CASCADE,
    option_value VARCHAR(255) NOT NULL
);

-- 4. Таблица Значений контейнеров (Связь много-ко-многим для EAV)
CREATE TABLE container_values (
    id SERIAL PRIMARY KEY,
    container_id INT REFERENCES containers(id) ON DELETE CASCADE,
    property_id INT REFERENCES properties(id) ON DELETE CASCADE,
    value VARCHAR(255)
);

INSERT INTO properties (id, name, data_type) VALUES 
(1, 'Длина', 'ENUM'),
(2, 'Высота', 'ENUM'),
(3, 'Тип перевозимого груза', 'ENUM');

INSERT INTO property_options (property_id, option_value)
VALUES
(1, '20 фт'),
(2, '8.6 фт'),
(3, 'генеральный'),
(3, 'жидкий'),
(3, 'газообразный');

INSERT INTO containers (id, name) VALUES 
(1, '20 фт стандартный контейнер'),
(2, '20 фт танк-контейнер');

INSERT INTO container_values (container_id, property_id, value) VALUES 
(1, 1, '20 фт'),
(1, 2, '8.6 фт'),
(1, 3, 'генеральный');

INSERT INTO container_values (container_id, property_id, value) VALUES 
(2, 1, '20 фт'),
(2, 2, '8.6 фт'),
(2, 3, 'жидкий'),
(2, 3, 'газообразный');

SELECT setval('containers_id_seq', (SELECT MAX(id) FROM containers));
SELECT setval('properties_id_seq', (SELECT MAX(id) FROM properties));
SELECT setval('property_options_id_seq', (SELECT MAX(id) FROM property_options));
SELECT setval('container_values_id_seq', (SELECT MAX(id) FROM container_values));