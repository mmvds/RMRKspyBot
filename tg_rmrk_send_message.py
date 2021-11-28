import psycopg2
import random
import time
from tg_rmrk_datatools import *
from tg_rmrk_collections import *
from tg_rmrk_estimation import *
from tg_rmrk_config import *
from telegram import ParseMode, ReplyKeyboardMarkup

# Send message


def send_message(conn, bot, db, nft_metadata, send_text, messages_list):
    try_text = False
    send_again = True
    send_attempt = 0
    if random.random() < 0.4:
        send_text += "\nPlease <a href='https://devpost.com/software/tools-and-apps-rmrkspybot'>vote for this Bot</a>\n"
    # Try to send as a photo
    while send_again and send_attempt < 10:
        send_again = False
        if nft_metadata.get('image', ''):
            photo_object = nft_metadata['image']
            db.execute(
                f"SELECT * FROM tg_images WHERE image_id='{nft_metadata['image'].split('/')[-1]}';")
            if db.rowcount > 0:
                if db.fetchone()[1]:
                    smallsize_name = f"./small_size/{nft_metadata['image'].split('/')[-1]}.png"
                    photo_object = open(smallsize_name, 'rb')
                else:
                    try_text = True
            if not try_text:
                try:
                    bot.send_photo(
                        chat_id=messages_list[0],
                        photo=photo_object,
                        caption=send_text,
                        parse_mode=ParseMode.HTML,
                        timeout=30)
                except Exception as e:
                    print(
                        time.ctime(),
                        round(
                            time.time()),
                        str(messages_list),
                        ':send_mail:',
                        e)
                    print(nft_metadata['image'])
                    if len(messages_list[1]) > 20:
                        nft_id = messages_list[1]
                    else:
                        nft_id = messages_list[2]
                    if ('file identifier' in str(e)) or (
                            'Failed to get http url content' in str(e)):
                        if kanaria_birds_ids_str in nft_id:
                            db.execute(
                                f"DELETE FROM tg_nft_metadata WHERE nft_id='{nft_id}';")
                            conn.commit()
                            db.execute(
                                f"SELECT metadata FROM nfts_v2 WHERE id='{nft_id}';")
                            metadata_url = db.fetchone()[0]
                            nft_metadata = fetch_metadata(
                                db, nft_id, metadata_url)
                        else:
                            convert_image(conn, db, nft_metadata['image'])
                        send_again = True
                        send_attempt += 1
                    elif ('blocked by the user' in str(e)) or ('user is deactivated' in str(e)):
                        db.execute(
                            f'UPDATE tg_users set is_active=False where id={messages_list[0]};')
                    else:
                        try_text = True
        else:
            try_text = True

    # Send as a text
    if try_text or send_attempt >= 10:
        send_text = nft_metadata.get('image', '') + '\n' + send_text
        try:
            bot.send_message(
                chat_id=messages_list[0],
                text=send_text,
                parse_mode=ParseMode.HTML)
        except Exception as e:
            print(
                time.ctime(),
                round(
                    time.time()),
                str(messages_list),
                ':send_mail:',
                e)
            if ('blocked by the user' in str(e)) or (
                    'user is deactivated' in str(e)):
                db.execute(
                    f'update tg_users set is_active=False where id={messages_list[0]};')

# Send record message to record channel


def send_record_message_to_channel(
        conn, bot, db, record_type, record_period, birds_record):
    nft_price, nft_id, nft_block = birds_record
    db.execute("SELECT * FROM tg_ksm_exchange_rate")
    ksm_exchange_rate = db.fetchone()[0]

    if record_type == 'item':
        db.execute(
            f"SELECT rarity, type, name FROM tg_items_info WHERE nft_id = '{nft_id}';")
        nft_rarity, nft_type, nft_name = db.fetchone()
        nft_name = nft_name.replace("'", "''")
        db.execute(f"SELECT metadata FROM nfts_v2 WHERE id = '{nft_id}';")
        send_text, nft_metadata = extract_header_info(
            db, nft_id, db.fetchone()[0])
        usd_price = to_ksm(nft_price) * Decimal(ksm_exchange_rate)
        send_text = f'<b>New {record_period.upper()} {record_type} record!</b>\n<a href="{kanaria_market_url}{nft_id}">Kanaria {nft_name} NFT was SOLD for {to_ksm(nft_price):.2f} KSM (~{usd_price:.2f}$)!</a>\n\n' + send_text
        send_text += estimate_item(db, nft_rarity, nft_type, nft_name)[0]

    elif record_type == 'bird':
        db.execute(f"SELECT * FROM tg_birds_info WHERE nft_id = '{nft_id}';")
        if db.rowcount > 0:
            send_text, nft_metadata = extract_header_info(
                db, nft_id, db.fetchone()[0])
            usd_price = to_ksm(nft_price) * Decimal(ksm_exchange_rate)
            send_text = f'<b>New {record_period.upper()} {record_type} record!</b>\n<a href="{kanaria_market_url}{nft_id}">Kanaria Bird NFT was SOLD for {to_ksm(nft_price):.2f} KSM (~{usd_price:.2f}$)!</a>\n\n' + send_text
            send_text += estimate_bird(db, nft_id, 'channel')[0]

    elif record_type == 'singular':
        db.execute(f"SELECT metadata FROM nfts_vlite WHERE id = '{nft_id}';")
        send_text, nft_metadata = extract_header_info(
            db, nft_id, db.fetchone()[0])
        usd_price = to_ksm(nft_price, 'singular') * Decimal(ksm_exchange_rate)
        send_text = f"<b>New {record_period.upper()} {record_type} record!</b>\n<a href='{singular_market_url}{nft_id}'>Singular NFT was SOLD for {to_ksm(nft_price,'singular'):.2f} KSM (~{usd_price:.2f}$)!</a>\n\n" + send_text

    send_text += "\nMore info in @RMRKspyBot\n"

    send_message(
        conn, bot, db, nft_metadata, send_text, [
            tg_allowed_channels[0], nft_id])
    conn.commit()

# Send a list of messages


def send_messages(bot, job):
    conn = psycopg2.connect(dbname=pg_db, user=pg_login,
                            password=pg_pass, host=pg_host)
    conn.set_client_encoding('UTF8')
    db = conn.cursor()

    db.execute("SELECT * FROM tg_ksm_exchange_rate")
    ksm_exchange_rate = db.fetchone()[0]

    db.execute(
        f"DELETE FROM tg_changes_messages WHERE user_id NOT IN (SELECT id FROM tg_users WHERE is_active);")
    conn.commit()
    db.execute(f"SELECT * FROM tg_changes_messages ORDER BY block LIMIT 10;")
    send_changes_messages = db.fetchall()
    for send_change_messages in send_changes_messages:
        user_id, nft_id, old_value, new_value, block, field, optype, metadata, nft_url, version = send_change_messages

        db.execute(
            f"DELETE FROM tg_changes_messages WHERE user_id={user_id} AND nft_id='{nft_id}' AND block={block} AND field='{field}';")
        send_text, nft_metadata = extract_header_info(db, nft_id, metadata)

        # Send following NFT messages
        if field == 'forsale':
            if version == 'v1':
                old_value = to_ksm(old_value, 'singular')
                new_value = to_ksm(new_value, 'singular')
            else:
                old_value = to_ksm(old_value)
                new_value = to_ksm(new_value)

        if optype == 'LIST' and field == 'forsale':
            if new_value > 0.0:
                send_text += f'<a href="{nft_url}">NFT RMRK{version} was LISTED for {new_value:.2f} KSM (~{Decimal(new_value) * Decimal(ksm_exchange_rate):.2f}$)! old_value price {old_value:.2f} KSM</a>\n'
            else:
                send_text += f'<a href="{nft_url}">NFT RMRK{version} was REMOVED from listing!</a>\n'

        elif optype == 'BUY' and field == 'forsale':
            send_text += f'<a href="{nft_url}">NFT RMRK{version} was SOLD for {old_value:.2f} KSM (~{Decimal(old_value) * Decimal(ksm_exchange_rate):.2f}$)!</a>\n'

        elif optype == 'BURN' or optype == 'CONSUME' and field == 'burned':
            send_text += f'<a href="{nft_url}">NFT RMRK{version} was BURNED!</a>\n'

        elif optype == 'SEND' and field == 'owner':
            if version == 'v1':
                send_text += f'<a href="{nft_url}">NFT RMRK{version}</a> was sent to <a href="{sub_id_url}{new_value}">{new_value}</a>\n'
            else:
                db.execute(f"SELECT * FROM nfts_v2 WHERE id = '{old_value}';")
                if db.rowcount != 0:
                    send_text += f'<a href="{nft_url}">NFT RMRK{version}</a> was Unequipped to <a href="{sub_id_url}{new_value}">{new_value}</a>\n'
                else:
                    db.execute(
                        f"SELECT * FROM nfts_v2 WHERE id = '{new_value}';")
                    if db.rowcount != 0:
                        send_text += f'<a href="{nft_url}">NFT RMRK{version}</a> was Equipped to <a href="{kanaria_market_url}{nft_id}">Kanaria NFT</a>\n'
                    else:
                        send_text += f'<a href="{nft_url}">NFT RMRK{version}</a> was sent to <a href="{sub_id_url}{new_value}">{new_value}</a>\n'
        else:
            conn.commit()
            continue

        send_text += f'\nUnsubscribe from these messages /unfollow ❌'
        send_message(
            conn,
            bot,
            db,
            nft_metadata,
            send_text,
            send_change_messages)
        conn.commit()

    # Send listed NFTs messages
    db.execute(
        f"DELETE FROM tg_forsale_messages WHERE user_id NOT IN (SELECT id FROM tg_users WHERE is_active);")
    conn.commit()
    db.execute(f"SELECT * FROM tg_forsale_messages ORDER BY block LIMIT 10;")
    send_forsale_messages = db.fetchall()
    for send_forsale_message in send_forsale_messages:
        nft_id = send_forsale_message[3]
        db.execute(
            f"DELETE FROM tg_forsale_messages WHERE user_id={send_forsale_message[0]} AND type='{send_forsale_message[1]}' AND nft_id='{nft_id}' AND block={send_forsale_message[5]};")
        send_text, nft_metadata = extract_header_info(
            db, nft_id, send_forsale_message[6])
        usd_price = Decimal(
            send_forsale_message[4]) * Decimal(ksm_exchange_rate)
        send_text += f'<a href="{kanaria_market_url}{nft_id}">Kanaria {send_forsale_message[1]} NFT was LISTED for {send_forsale_message[4]:.2f} KSM (~{usd_price:.2f}$)!</a>\n'
        if send_forsale_message[1] == 'item':
            db.execute(
                f"SELECT rarity, type, name FROM tg_items_info WHERE nft_id = '{nft_id}';")
            nft_rarity, nft_type, nft_name = db.fetchone()
            nft_name = nft_name.replace("'", "''")
            send_text += estimate_item(db, nft_rarity, nft_type, nft_name)[0]
        elif send_forsale_message[1] == 'bird':
            send_text += estimate_bird(db, nft_id, "header")[0]
        send_text += f'\nUnsubscribe from these messages /{send_forsale_message[1]}s_forsale_{send_forsale_message[2]} ❌'
        send_message(
            conn,
            bot,
            db,
            nft_metadata,
            send_text,
            send_forsale_message)
        conn.commit()

    # Send sold NFTs messages
    db.execute(
        f"DELETE FROM tg_buy_messages WHERE user_id NOT IN (SELECT id FROM tg_users WHERE is_active);")
    conn.commit()
    db.execute(f"SELECT * FROM tg_buy_messages ORDER BY block LIMIT 10;")
    send_buy_messages = db.fetchall()
    for send_buy_message in send_buy_messages:
        send_buy_message = list(send_buy_message)
        send_buy_message[2] = send_buy_message[2].replace("'", "''")
        db.execute(
            f"DELETE FROM tg_buy_messages WHERE user_id={send_buy_message[0]} AND type='{send_buy_message[1]}' AND nft_id='{send_buy_message[2]}' AND block={send_buy_message[4]};")
        nft_id = send_buy_message[2]
        send_text, nft_metadata = extract_header_info(
            db, nft_id, send_buy_message[5])
        usd_price = Decimal(send_buy_message[3]) * Decimal(ksm_exchange_rate)
        if send_buy_message[1] == "singular":
            send_text += f'<a href="{singular_market_url}{nft_id}">Singular NFT was SOLD for {send_buy_message[3]:.2f} KSM (~{usd_price:.2f}$)!</a>\n'
            print(f"{singular_market_url}{nft_id}")
            if send_buy_message[0] > 0:
                send_text += f'\nUnsubscribe from these messages /singular_buy ❌'
            else:
                send_text += f'\nMore info in @RMRKspyBot'

        elif send_buy_message[1] == "bird":
            send_text += f'<a href="{kanaria_market_url}{nft_id}">Kanaria Bird NFT was SOLD for {send_buy_message[3]:.2f} KSM (~{usd_price:.2f}$)!</a>\n'
            if send_buy_message[0] > 0:
                send_text += estimate_bird(db, nft_id, "header")[0]
                send_text += f'\nUnsubscribe from these messages /birds_buy ❌'
            else:
                send_text += estimate_bird(db, nft_id, "channel")[0]
                send_text += f'\nMore info in @RMRKspyBot'

        elif send_buy_message[1] == "item":
            send_text += f'<a href="{kanaria_market_url}{nft_id}">Kanaria Item NFT was SOLD for {send_buy_message[3]:.2f} KSM (~{usd_price:.2f}$)!</a>\n'
            db.execute(
                f"SELECT rarity, type, name FROM tg_items_info WHERE nft_id = '{nft_id}';")
            nft_rarity, nft_type, nft_name = db.fetchone()
            nft_name = nft_name.replace("'", "''")
            send_text += estimate_item(db, nft_rarity, nft_type, nft_name)[0]
            if send_buy_message[0] > 0:
                send_text += f'\nUnsubscribe from these messages /items_buy ❌'
            else:
                send_text += f'\nMore info in @RMRKspyBot'

        send_message(conn, bot, db, nft_metadata, send_text, send_buy_message)
        conn.commit()
    conn.close()
