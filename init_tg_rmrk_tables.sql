\SET kanaria_sales_channel <kanaria_sales_channel_id>;
\SET singular_sales_channel <singular_sales_channel_id>;

DROP TABLE IF EXISTS tg_lastblocks;
DROP TABLE IF EXISTS tg_users;
DROP TABLE IF EXISTS tg_buy;
DROP TABLE IF EXISTS tg_forsale;
DROP TABLE IF EXISTS tg_follows;
DROP TABLE IF EXISTS tg_buy_messages;
DROP TABLE IF EXISTS tg_block_history;
DROP TABLE IF EXISTS tg_forsale_messages;
DROP TABLE IF EXISTS tg_changes_messages;
DROP TABLE IF EXISTS tg_nft_metadata;
DROP TABLE IF EXISTS tg_ksm_exchange_rate;
DROP TABLE IF EXISTS tg_items_info;
DROP TABLE IF EXISTS tg_birds_info;
DROP TABLE IF EXISTS tg_birds_gems_info;
DROP TABLE IF EXISTS tg_birds_traits_amount;
DROP TABLE IF EXISTS tg_birds_common_rate;
DROP TABLE IF EXISTS tg_record;
DROP TABLE IF EXISTS tg_images;

CREATE TABLE tg_lastblocks (lastblock_v1 integer, lastblock_v2 integer);
INSERT INTO tg_lastblocks(lastblock_v1, lastblock_v2) VALUES ((select * from lastblock_vlite) - 1,(select * from lastblock_v2) - 1);
CREATE TABLE tg_users (id bigint primary key, tg_user text, is_active boolean, last_action integer);
CREATE TABLE tg_buy (user_id bigint primary key, singular_buy numeric(25, 10), birds_buy numeric(25, 10), items_buy numeric(25, 10));
INSERT INTO tg_users VALUES (:kanaria_sales_channel, 'kanariasales', TRUE, 0);
INSERT INTO tg_users VALUES (:singular_sales_channel, 'singularsales', TRUE, 0);
INSERT INTO tg_buy VALUES (:kanaria_sales_channel, 0.00001, 0, 0);
INSERT INTO tg_buy VALUES (:singular_sales_channel, 0, 0.00001, 0.00001);
CREATE TABLE tg_forsale (user_id bigint primary key, birds_forsale_any numeric(25, 10), birds_forsale_limited numeric(25, 10), 
    birds_forsale_rare numeric(25, 10), birds_forsale_super numeric(25, 10), birds_forsale_founder numeric(25, 10), 
    items_forsale_any numeric(25, 10), items_forsale_legendary numeric(25, 10), items_forsale_epic numeric(25, 10), 
    items_forsale_rare numeric(25, 10), items_forsale_uncommon numeric(25, 10), items_forsale_common numeric(25, 10));
CREATE TABLE tg_follows (user_id bigint, nft_id text, nft_name text, nft_url text, version text);
CREATE TABLE tg_buy_messages (user_id bigint, type text, nft_id text, price numeric(25, 10), block integer, metadata text);
CREATE TABLE tg_block_history (block integer primary key, approx_time integer);
CREATE TABLE tg_forsale_messages (user_id bigint, type text, rarity text, nft_id text, price numeric(25, 10), block integer, metadata text);
CREATE TABLE tg_changes_messages(user_id bigint, nft_id text, old text, new text, block integer, field text, optype text, metadata text, nft_url text, version text);
CREATE TABLE tg_ksm_exchange_rate (ksm_exchange_rate numeric(25, 10));
INSERT INTO tg_ksm_exchange_rate(ksm_exchange_rate) VALUES(100);
CREATE TABLE tg_nft_metadata (nft_id text primary key, metadata jsonb);
CREATE TABLE tg_items_info(nft_id text primary key, rarity text, type text, name text);
CREATE TABLE tg_birds_info(nft_id text primary key, rarity text, theme text, name text, head text, eyes text, body text, tail text, wingleft text, wingright text, feet text, resource_amount integer, trait_score float, trait_place integer);
CREATE TABLE tg_birds_gems_info(bird_id text primary key, gems jsonb, trait_score float, trait_place integer);
CREATE TABLE tg_birds_traits_amount(nft_id text primary key, rarity integer, theme integer, head integer, eyes integer, body integer, tail integer, wingleft integer, wingright integer, feet integer, resource_amount integer);
CREATE TABLE tg_birds_common_rate(nft_id text primary key, trait_score float, trait_place integer);
CREATE TABLE tg_record(record_period text, record_type text, nft_id text, block integer);
INSERT INTO tg_record VALUES('daily','singular','', 0);
INSERT INTO tg_record VALUES('weekly','singular','', 0);
INSERT INTO tg_record VALUES('monthly','singular','', 0);
INSERT INTO tg_record VALUES('daily','bird','', 0);
INSERT INTO tg_record VALUES('weekly','bird','', 0);
INSERT INTO tg_record VALUES('monthly','bird','', 0);
INSERT INTO tg_record VALUES('daily','item','', 0);
INSERT INTO tg_record VALUES('weekly','item','', 0);
INSERT INTO tg_record VALUES('monthly','item','', 0);
CREATE TABLE tg_images(image_id text, is_converted boolean);