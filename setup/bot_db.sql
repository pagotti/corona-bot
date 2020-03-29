/*
Schema do banco Postgre SQL do bot
Substitua "yldzrofu" pelo nome do usuário do seu banco

*/

SET default_tablespace = '';

SET default_with_oids = false;

CREATE SEQUENCE public.jobcache_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER TABLE public.jobcache_id_seq OWNER TO "yldzrofu";

CREATE TABLE public.jobcache (
    id bigint DEFAULT nextval('public.jobcache_id_seq'::regclass) NOT NULL,
    job_id character varying(37),
    interval int NOT NULL,
    region character varying(50),
    chat_id character varying(37),
	repeat boolean DEFAULT TRUE,
	only_new boolean DEFAULT FALSE,  
    last_cases int DEFAULT 0,
	last_deaths int DEFAULT 0,
	last_recovery int DEFAULT 0,
    create_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.jobcache OWNER TO "yldzrofu";

ALTER TABLE ONLY public.jobcache
    ADD CONSTRAINT jobcache_pkey PRIMARY KEY (id);


CREATE SEQUENCE public.botlog_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.botlog_id_seq OWNER TO "yldzrofu";

CREATE TABLE public.botlog (
    id bigint DEFAULT nextval('public.botlog_id_seq'::regclass) NOT NULL,
    chat_id character varying(37) NOT NULL,
    user_name character varying(50),
    command character varying(20),
    args character varying(200),
    create_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.botlog OWNER TO "yldzrofu";


ALTER TABLE ONLY public.botlog
    ADD CONSTRAINT botlog_pkey PRIMARY KEY (id);


CREATE SEQUENCE public.cases_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER TABLE public.cases_id_seq OWNER TO "yldzrofu";

CREATE TABLE public.cases (
    id bigint DEFAULT nextval('public.cases_id_seq'::regclass) NOT NULL,
    data_source character varying(50),
    region character varying(50),
    cases int DEFAULT 0,
	deaths int DEFAULT 0,
	recovery int DEFAULT 0,
	source_date timestamp with time zone,
    create_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.cases OWNER TO "yldzrofu";

ALTER TABLE ONLY public.cases
    ADD CONSTRAINT cases_pkey PRIMARY KEY (id);
