CREATE DATABASE dados_dashboard;
USE dados_dashboard;

CREATE TABLE dados (
    idDado BIGINT AUTO_INCREMENT, 
    criacaoInsert DATE DEFAULT (CURRENT_DATE),
    modeloEquip VARCHAR(255),
    numSerieEquip VARCHAR(255),
    ipEquip VARCHAR(45),
    portaEquip INT,
    statusEquip ENUM('Conectado', 'Desconectado'),
    dataUltimaConexao DATE,
    horaUltimaConexao TIME,
    dataUltimoRegistro DATE,
    PRIMARY KEY (idDado, criacaoInsert, cliente)
);
