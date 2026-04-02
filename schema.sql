
create table if not exists contratti (

    id bigint generated always as identity primary key,

    numero_fattura integer,

    nome text,
    cognome text,

    data_nascita date,
    luogo_nascita text,

    indirizzo text,
    citta text,
    nazione text,

    telefono text,
    email text,

    codice_fiscale text,

    numero_patente text,
    rilascio_patente date,
    scadenza_patente date,

    targa text,

    prezzo numeric,
    deposito numeric,

    note text,

    data_contratto timestamp default now(),

    privacy boolean default false,

    patente_fronte text,
    patente_retro text,
    firma text

);

create table if not exists contatore_fatture (

    anno integer primary key,
    ultimo_numero integer

);

insert into contatore_fatture (anno, ultimo_numero)
values (extract(year from now()), 0)
on conflict do nothing;

