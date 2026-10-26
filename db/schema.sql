-- Tabla de alimentos
CREATE TABLE IF NOT EXISTS food (
    id SERIAL PRIMARY KEY,
    fdc_id INT NOT NULL UNIQUE,
    name VARCHAR(150) NOT NULL,  -- description
    category VARCHAR(50), -- foodCategory
    serving_g NUMERIC(10, 2) CHECK (serving_g > 0),
    source VARCHAR(100) default 'USDA'  -- dataType
);

-- Tabla de nutrientes
CREATE TABLE IF NOT EXISTS nutrient (
    id SERIAL PRIMARY KEY,
    usda_id INT NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    unit VARCHAR(20) NOT NULL
);

-- Tabla de relación entre alimentos y nutrientes
CREATE TABLE IF NOT EXISTS food_nutrient (
    food_id INT REFERENCES food(id) ON DELETE CASCADE,
    nutrient_id INT REFERENCES nutrient(id) ON DELETE CASCADE,
    amount NUMERIC(10, 2) NOT NULL CHECK (amount >= 0),
    PRIMARY KEY (food_id, nutrient_id)
);

-- Tabla auxiliar para clasificar nutrientes en categorías
CREATE TABLE IF NOT EXISTS nutrient_catalog (
    usda_id      INT         PRIMARY KEY,
    nutrient_nbr VARCHAR(10) NOT NULL,
    category     VARCHAR(50) NOT NULL DEFAULT 'other'
);

-- Tabla de usuarios
CREATE TABLE IF NOT EXISTS user_profile (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    age INT CHECK (age >= 0),
    sex VARCHAR(10) CHECK (sex IN ('male', 'female', 'other', 'all')),
    condition VARCHAR(20) CHECK (condition IN ('pregnancy', 'lactation', 'none')) default 'none',
    weight NUMERIC(5, 2) CHECK (weight >= 0),
    height NUMERIC(5, 2) CHECK (height >= 0),
    goal VARCHAR(50) CHECK (goal IN ('weight_loss', 'weight_gain', 'maintenance')) default 'maintenance',
    activity_level VARCHAR(20) CHECK (activity_level IN ('sedentary', 'low_active', 'active', 'very_active')) default 'sedentary'
);

-- Tabla de recomendaciones diarias de nutrientes
CREATE TABLE IF NOT EXISTS recommendation (
    id SERIAL PRIMARY KEY,
    nutrient_id INT REFERENCES nutrient(usda_id) ON DELETE CASCADE,
    sex VARCHAR(10) CHECK (sex IN ('male', 'female', 'other')),
    condition VARCHAR(20) CHECK (condition IN ('pregnancy', 'lactation', 'none')) default 'none',
    age_min INT CHECK (age_min >= 0),
    age_max INT CHECK (age_max >= 0),
    dri_value NUMERIC(10, 2) NOT NULL CHECK (dri_value >= 0),
    ul_value NUMERIC(10, 2) CHECK (ul_value >= 0),
    source VARCHAR(100),
    CONSTRAINT valid_age_range CHECK (age_min < age_max)
);

-- Tabla de registro diario de alimentos consumidos por los usuarios
CREATE TABLE IF NOT EXISTS daily_log (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES user_profile(id) ON DELETE CASCADE,
    food_id INT REFERENCES food(id) ON DELETE CASCADE,
    log_date DATE NOT NULL,
    quantity NUMERIC(10, 2) NOT NULL CHECK (quantity >= 0),
    UNIQUE (user_id, log_date, food_id)
);