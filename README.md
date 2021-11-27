# rmrk_spy_bot
RMRK spy bot https://t.me/RMRKspyBot for rmrk hacktoberfest https://rmrk.devpost.com/

1) Birds and items price and rarity estimation

2) Reports RMRKv1,2 sales above a certain threshold

3) Monitor cheap items and birds for sale

4) Track the statuses of NFTs

Full description https://devpost.com/software/tools-and-apps-rmrkspybot

## Requirements
1) Install required modules

pip install -r requirements.txt

2) This bot uses rmrk dump files parsed to Postgresql DB
https://github.com/mmvds/rmrk2psql

## Сonfiguration
1) Edit init_tg_rmrk_tables.sql file 

set <kanaria_sales_channel_id> and <singular_sales_channel_id> for telegram channels

2) To init telegram tables, use psql "postgresql://$pg_login:$pg_pass@$pg_host/$pg_db_name" -f init_tg_rmrk_tables.sql

3) Change tg_rmrk_config.py file:

```#postgres db
pg_login = "<postgres_login>"
pg_pass = "<postgres_password>"
pg_db = "<postgres_database_name>"
pg_host = "<postgres_host>"

#telegram token
tg_token = "<telegram_token>"

#admin tg user id
tg_admin_id = <tg_admin_id>

#record channel id, singular sales channel id, kanaria sales channel id
tg_allowed_channels = [<record_sales_channel_id>, <kanaria_sales_channel_id>, <singular_sales_channel_id>]

#used endpoints
kanaria_market_url = "https://kanaria.rmrk.app/catalogue/"
singular_market_url = "https://singular.rmrk.app/collectibles/"
sub_id_url = "https://sub.id/#/"
ipfs_gateway_url = "https://gateway.pinata.cloud/"
kanaria_nft_api_url = '<birds_img_API_gateway>'

#Kanaria and Singular marketplace fee 5 a 2%
kanaria_fee = 5
singular_fee = 2
