create_command_sql = """CREATE TABLE Masters (
    id INTEGER PRIMARY KEY,
    firstName TEXT NOT NULL,
    lastName TEXT NOT NULL,
    experienceYears INTEGER NOT NULL,
    link_foto TEXT NOT NULL,
    description TEXT NOT NULL
);

CREATE TABLE Services (
    id INTEGER PRIMARY KEY,
    serviceName TEXT NOT NULL,
    durationMinutes INTEGER NOT NULL
);

CREATE TABLE MasterServices (
    masterId INTEGER,
    serviceId INTEGER,
    price REAL NOT NULL,
    PRIMARY KEY (masterId, serviceId),
    FOREIGN KEY(masterId) REFERENCES Masters(id),
    FOREIGN KEY(serviceId) REFERENCES Services(id)
);

CREATE TABLE MasterTime (
    masterId INTEGER,
    dayDate TEXT NOT NULL,
    start_0800 TEXT,
    start_0900 TEXT,
    start_1000 TEXT,
    start_1100 TEXT,
    start_1200 TEXT,
    start_1300 TEXT,
    start_1400 TEXT,
    start_1500 TEXT,
    start_1600 TEXT,
    start_1700 TEXT,
    start_1800 TEXT,
    start_1900 TEXT,
    PRIMARY KEY (masterId, dayDate),
    FOREIGN KEY(masterId) REFERENCES Masters(id)
);

CREATE TABLE Clients (
    id INTEGER PRIMARY KEY,
    firstName TEXT NOT NULL,
    phoneNumber TEXT NOT NULL,
    eMail TEXT
);

CREATE TABLE Record (
    id INTEGER PRIMARY KEY,
    clientFirstName TEXT NOT NULL,
    clientPhoneNumber TEXT NOT NULL,
    masterId INTEGER NOT NULL,
    serviceId INTEGER NOT NULL,
    appointmentDate TEXT NOT NULL,
    appointmentTime TEXT NOT NULL,
    remind INTEGER,
    FOREIGN KEY(masterId) REFERENCES Masters(id),
    FOREIGN KEY(serviceId) REFERENCES Services(id)
);
    
    
INSERT INTO Masters (firstName, lastName, experienceYears, link_foto, description)
VALUES ('Петр', 'Иванов', 10, "image/bobr.jpg", "Лучшая техника стрижки, отпыт работы 10 лет"), ('Ольга', 'Сидорова', 5, "image/chebur.jpg", "Первое место по мойке волос"), ('Эполит', 'Мамеев', 7, "image/bobri.jpg", "Парикмахер в 5 поколении");

INSERT INTO Services (serviceName, durationMinutes)
VALUES ('Стрижка мужская', 60), ('Стрижка женская', 60), ('Стрижка бороды', 30),
       ('Мытье головы', 60), ('Колирование седины', 60), ('Укладка', 60), ('Бритье усов и бороды', 30);


INSERT INTO MasterServices (masterId, serviceId, price) VALUES
(1, 1, 1000),
(2, 1, 900),
(3, 1, 800),
(3, 2, 1200),
(1, 3, 500),
(2, 3, 400),
(3, 3, 500),
(1, 4, 800),
(2, 4, 700),
(1, 5, 600),
(2, 5, 500),
(3, 5, 800),
(1, 6, 700),
(1, 7, 1000),
(2, 6, 700);  
    
    
    

"""
