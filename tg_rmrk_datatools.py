# Datatools
import pyvips
import requests
import random
import json
import psycopg2
import cryptocompare
from decimal import Decimal
from tg_rmrk_collections import *
from tg_rmrk_config import *

# Convert to ksm values


def to_ksm(price, fee_type="kanaria"):
    if fee_type == "kanaria":
        return Decimal(price) / Decimal(10**12) / \
            Decimal(1 - kanaria_fee / 100)
    else:
        return Decimal(price) / Decimal(10**12) / \
            Decimal(1 - singular_fee / 100)

# Get current KSM exchange rate


def update_ksm_exchange_rate(bot, job):
    conn = psycopg2.connect(dbname=pg_db, user=pg_login,
                            password=pg_pass, host=pg_host)
    conn.set_client_encoding('UTF8')
    db = conn.cursor()
    try:
        ksm_exchange_rate = Decimal(
            cryptocompare.get_price(
                "KSM", currency='USD')['KSM']['USD'])
        db.execute(
            f"UPDATE tg_ksm_exchange_rate SET ksm_exchange_rate={ksm_exchange_rate:.2f}")
        conn.commit()
    except Exception as e:
        print(str(e))
    conn.close()

# Convert full size images to Xx500 images (possible to send)


def convert_image(conn, db, url):
    try:
        r = requests.get(url)
        image_id = url.split('/')[-1]
        try:
            fullsize_name = f"./full_size/{image_id}"
            smallsize_name = f"./small_size/{image_id}.png"
            with open(fullsize_name, 'wb') as f:
                f.write(r.content)
            image = pyvips.Image.thumbnail(fullsize_name, 500)
            image.write_to_file(smallsize_name)
            db.execute(f"INSERT INTO tg_images VALUES('{image_id}', TRUE);")
            conn.commit()
            return True
        except BaseException:
            db.execute(f"INSERT INTO tg_images VALUES('{image_id}', FALSE);")
            conn.commit()
            return False
    except BaseException:
        return False

# Extract header info for NFT


def extract_header_info(db, nft_id, metadata_url):
    nft_metadata = fetch_metadata(db, nft_id, metadata_url)
    send_text = ""
    if nft_metadata.get('name', ''):
        send_text += f"<b>{nft_metadata['name']}</b>\n"
    if kanaria_birds_ids_str not in nft_id:
        if 'properties' in nft_metadata:
            send_text += '\n'
            for p in nft_metadata['properties']:
                if p == 'egg_rot_percentage':
                    continue
                if 'percentage' in p:
                    try:
                        nft_metadata['properties'][p]['value'] = str(
                            round(float(nft_metadata['properties'][p]['value']), 2)) + '%'
                    except BaseException:
                        pass
                send_text += f"{p}: <b>{nft_metadata['properties'][p].get('value','')}</b>\n"
            send_text = send_text.replace(
                "legendary",
                "🔸legendary").replace(
                "epic",
                "🔹epic").replace(
                "rare",
                "🔺rare").replace(
                "uncommon",
                "▫️uncommon")
            send_text += '\n'

    return send_text, nft_metadata

# Get metadata by nft id and metadata_url


def fetch_metadata(db, nft_id, metadata_url):
    nft_metadata = {}
    db.execute(
        f"SELECT metadata FROM tg_nft_metadata WHERE nft_id='{nft_id}';")
    if db.rowcount != 0:
        nft_metadata = db.fetchone()[0]
    elif metadata_url:
        try:
            nft_metadata = requests.get(
                metadata_url.replace(
                    'ipfs://', ipfs_gateway_url)).json()
        except BaseException:
            nft_metadata = {}
        if kanaria_birds_ids_str in nft_id:
            nft_metadata['image'] = requests.get(f'{kanaria_nft_api_url}{nft_id}').json()[
                'image'] + f"?random={random.randint(0,42)}"
            if 'theme' not in nft_metadata and 'Theme' not in nft_metadata:
                nft_metadata['theme'] = 'Defaultyellow'
        nft_metadata['image'] = nft_metadata.get(
            'image', '').replace(
            'ipfs://', ipfs_gateway_url)
        json_metadata = json.dumps(nft_metadata).replace("'", "''")
        db.execute(
            f"INSERT INTO tg_nft_metadata(nft_id, metadata) VALUES('{nft_id}','{json_metadata}');")
    return nft_metadata
