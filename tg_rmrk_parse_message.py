import psycopg2
import time
from telegram import ParseMode, ReplyKeyboardMarkup
from tg_rmrk_datatools import *
from tg_rmrk_collections import *
from tg_rmrk_estimation import *
from tg_rmrk_send_message import *
from tg_rmrk_config import *

# Parse telegram messages


def parse_message(bot, update):
    if update.message:
        update_message = update.message
    elif update.edited_message:
        update_message = update.edited_message
        print(f'{update_message.chat_id} {update_message.from_user.username} Sent edited message {update_message.text}')
    else:
        update_message = update.effective_message

        # If someone added our bot to another channel
        if update_message.chat_id not in tg_allowed_channels:
            answer = f'Bot was added to the channel {update_message.chat_id}\n'
            admins_chanel = bot.get_chat_administrators(
                chat_id=update_message.chat_id)
            for admin_chanel in admins_chanel:
                answer += f'<a href="tg://user?id={admin_chanel.user.id}">{admin_chanel.user.username}</a>\n'
            try:
                bot.send_message(
                    chat_id=update_message.chat_id,
                    text="Please don't add me to your channels! Good buy! :) @RMRKspyBot",
                    parse_mode=ParseMode.HTML)
            except Exception as e:
                print(time.ctime(), str(answer), ':', e)
            try:
                bot.forward_message(
                    chat_id=tg_admin_id,
                    from_chat_id=update_message.chat_id,
                    message_id=update_message.message_id)
                bot.leave_chat(chat_id=update_message.chat_id)
                bot.send_message(
                    chat_id=tg_admin_id,
                    text=answer,
                    parse_mode=ParseMode.HTML)
            except Exception as e:
                print(time.ctime(), str(answer), ':', e)
        else:
            return

    user_id = update_message.chat_id
    tg_user = update_message.from_user.username
    mt = update_message.text
    current_action = round(time.time())
    if not mt:
        return

    # Possible commands for bot
    commands = [
        '/start',
        'Follow',
        'Sold',
        'ForSale',
        'Estimate',
        '/birds_forsale',
        '/items_forsale',
        '/follow',
        '/unfollow',
        '/estimate',
        '/singular_buy',
        '/birds_buy',
        '/items_buy']
    if not any([x in mt for x in commands]):
        return
    conn = psycopg2.connect(dbname=pg_db, user=pg_login,
                            password=pg_pass, host=pg_host)
    conn.set_client_encoding('UTF8')
    db = conn.cursor()
    db.execute(f'SELECT * FROM tg_users WHERE id = {user_id}')
    user = db.fetchone()

    # Add new user
    if user is None:
        db.execute(
            f"INSERT INTO tg_users VALUES ({user_id},'{tg_user}',True,{current_action - 2});")
        db.execute(
            f"INSERT INTO tg_buy VALUES ({user_id},0.0,0.0,0.0) ON CONFLICT (user_id) DO NOTHING;")
        db.execute(
            f"INSERT INTO tg_forsale VALUES ({user_id},0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0) ON CONFLICT (user_id) DO NOTHING;")
        conn.commit()
        db.execute(f'SELECT * FROM tg_users WHERE id = {user_id}')
        user = db.fetchone()
    user = list(user)
    is_user_active, last_user_action = user[2], user[3]

    msg = ""
    if not is_user_active:
        msg += f'Welcome back!\n'

    # Buttons
    custom_keyboard = [['🔍Follow', '💰Estimate'], ['📈Sold', '📊ForSale']]
    reply_markup = ReplyKeyboardMarkup(custom_keyboard, resize_keyboard=True)

    # Reply to user messages less than once a second (anti-spam)
    if current_action - last_user_action > 0:
        if len(mt) < 30:
            parsed_val = Decimal("0" + re.sub(r"[^0-9.]", "", mt))
        else:
            parsed_val = 0

        # Estimate messages
        if any([x in mt for x in ('Estimate', '/estimate')]):
            msg = parse_estimate_message(
                conn, bot, db, user_id, mt, parsed_val, msg)

        # Follow messages
        elif any([x in mt for x in ('Follow', '/follow', '/unfollow')]):
            msg = parse_follow_message(
                conn, bot, db, user_id, mt, parsed_val, msg)

        # Buy messages
        elif any([x in mt for x in ('Sold', '/singular_buy', '/birds_buy', '/items_buy')]):
            msg = parse_buy_message(
                conn, bot, db, user_id, mt, parsed_val, msg)

        # Sale messages
        elif any([x in mt for x in ('ForSale', '/birds_forsale', '/items_forsale')]):
            msg = parse_forsale_message(
                conn, bot, db, user_id, mt, parsed_val, msg)
        else:
            msg += f'Please choose one of the actions\n'
        if msg:
            try:
                bot.send_message(
                    chat_id=user_id,
                    text=msg,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup)
            except Exception as e:
                print(time.ctime(), str(tg_user), str(user_id), mt, e)
        db.execute(
            f"UPDATE tg_users SET tg_user='{tg_user}', is_active=True, last_action={current_action} WHERE id = {user_id}")
        conn.commit()
    conn.close()


def parse_estimate_message(conn, bot, db, user_id, mt, parsed_val, msg):
    if 'Estimate' in mt:
        msg += "Bot will calculate the estimated price of Kanaria NFT (items or birds) based on the history of sales of similar NFTs\n"
        msg += "\nFormat:\n"
        msg += "/estimate Kanaria_Bird_or_Item_NFT_id_or_url_or_Bird_number\n"
        msg += "e.g. /estimate_7952 /estimate_full_7952\n"
        msg += '\n<a href="https://medium.com/@rybvic/kanaria-nft-price-estimation-be82c2976958">How it works</a>\n'
    elif '/estimate' in mt:
        print(user_id, mt)
        if '/estimate_full' in mt:
            estimation_type = 'full'
            mt = mt.replace('/estimate_full', '/estimate')
        else:
            estimation_type = 'short'
        estimate_id = mt[10:].strip().split("/")[-1].replace("'", "''")
        if parsed_val > 0 and parsed_val < 10000 and len(mt) < 50:
            db.execute(
                f"SELECT id FROM nfts_v2 WHERE collection='{kanaria_birds_ids_str}' and sn::int = {parsed_val};")
            if db.rowcount > 0:
                estimate_id = db.fetchone()[0]
        db.execute(
            f"SELECT id FROM nfts_v2 WHERE rootowner='{estimate_id}';")
        if db.rowcount > 0:
            send_message_only(
                    conn, bot, db, "It may take a few seconds, please wait...", user_id)
            send_text = estimate_wallet(db, estimate_id, estimation_type)[0]
            send_message_only(
                    conn, bot, db, send_text, user_id)
            return
        else:
            db.execute(
                f"SELECT rarity, type, name FROM tg_items_info WHERE nft_id = '{estimate_id}';")
            if db.rowcount > 0:
                #Estimate item
                nft_rarity, nft_type, nft_name = db.fetchone()
                nft_name = nft_name.replace("'", "''")
                db.execute(
                    f"SELECT metadata FROM nfts_v2 WHERE id = '{estimate_id}';")
                send_text, nft_metadata = extract_header_info(
                    db, estimate_id, db.fetchone()[0])
                send_text += estimate_item(db, nft_rarity, nft_type, nft_name)[0]
                send_message(
                    conn, bot, db, nft_metadata, send_text, [
                        user_id, estimate_id])
                conn.commit()
                return

            else:
                db.execute(
                    f"SELECT * FROM tg_birds_info WHERE nft_id = '{estimate_id}';")
                if db.rowcount > 0:
                    #Estimate bird
                    db.execute(
                        f"SELECT metadata FROM nfts_v2 WHERE id = '{estimate_id}';")
                    send_text, nft_metadata = extract_header_info(
                        db, estimate_id, db.fetchone()[0])
                    send_text += estimate_bird(db, estimate_id, estimation_type)[0]
                    send_message(
                        conn, bot, db, nft_metadata, send_text, [
                            user_id, estimate_id])
                    conn.commit()
                    return
                else:
                    msg += "Can't find Kanaria NFT item!\n"
                    msg += "Please use the following format:\n/estimate Kanaria_Bird_or_Item_NFT_id_or_url\n"
    return msg


def parse_follow_message(conn, bot, db, user_id, mt, parsed_val, msg):
    msg += "Bot will send a message in case of any action with NFT (1-30 min. update)\n\n"
    db.execute(
        f'SELECT * FROM tg_follows WHERE user_id = {user_id} ORDER BY nft_id')
    follows = db.fetchall()
    if 'follow' in mt:
        if '/unfollow' in mt and int(parsed_val) in range(1, len(follows) + 1):
            db.execute(
                f"DELETE FROM tg_follows WHERE user_id = {user_id} AND nft_id = '{follows[int(parsed_val) - 1][1]}';")
        elif '/follow' in mt:
            follow_id = mt[8:].strip().replace(kanaria_market_url, "").replace(
                singular_market_url, "").replace("'", "''")
            if parsed_val > 0 and parsed_val < 10000:
                db.execute(
                    f"select id from nfts_v2 where collection='{kanaria_birds_ids_str}' and sn::int = {parsed_val};")
                if db.rowcount > 0:
                    follow_id = db.fetchone()[0]
            if len(follows) >= 10:
                msg += "Maximum tracked nft <b>10 per user</b>!\n"
            else:
                db.execute(
                    f"SELECT id, metadata FROM nfts_vlite WHERE id = '{follow_id}';")
                nft_url = ''
                if db.rowcount != 0:
                    nft_url = f'{singular_market_url}{follow_id}'
                    version = 'v1'
                else:
                    db.execute(
                        f"SELECT id, metadata FROM nfts_v2 WHERE id = '{follow_id}';")
                    if db.rowcount != 0:
                        nft_url = f'{kanaria_market_url}{follow_id}'
                        version = 'v2'
                    else:
                        msg += f"\nCan't find nft with ID {follow_id}\n"
                if nft_url:
                    nft_info = db.fetchone()
                    nft_name = fetch_metadata(
                        db, nft_info[0], nft_info[1]).get(
                        'name', '')

                    db.execute(
                        f"INSERT INTO tg_follows(user_id, nft_id, nft_name, nft_url, version) VALUES ({user_id}, '{follow_id}', '{nft_name}','{nft_url}', '{version}');")
        conn.commit()
        db.execute(
            f'SELECT * FROM tg_follows WHERE user_id = {user_id} ORDER BY nft_id;')
        follows = db.fetchall()

    for i in range(len(follows)):
        follow = [follows[i][0]]
        follow.extend([x.replace("'", "''") for x in follows[i][1:]])
        if follow[2]:
            nft_name = follow[2]
        else:
            nft_name = follow[1]
        msg += f'<b>{i + 1}.</b> <a href="{follow[3]}">{nft_name}</a> /unfollow_{i + 1}\n'
    msg += "\nFormat:\n"
    msg += "/follow rmrk_v1_or_v2_NFT_id\n"
    return msg


def parse_buy_message(conn, bot, db, user_id, mt, parsed_val, msg):
    db.execute(f'SELECT * FROM tg_buy WHERE user_id = {user_id}')
    singular_buy, birds_buy, items_buy = [
        Decimal(x) for x in db.fetchone()[1:]]
    mt = mt.lower()
    if '/singular_buy' in mt:
        singular_buy = parsed_val
        db.execute(
            f"UPDATE tg_buy set singular_buy={singular_buy} WHERE user_id = {user_id}")
        conn.commit()
    if '/birds_buy' in mt:
        birds_buy = parsed_val
        db.execute(
            f"UPDATE tg_buy set birds_buy={birds_buy} WHERE user_id = {user_id}")
        conn.commit()
    if '/items_buy' in mt:
        items_buy = parsed_val
        db.execute(
            f"UPDATE tg_buy set items_buy={items_buy} WHERE user_id = {user_id}")
        conn.commit()
    msg += "Bot will send a notification if someone <b>bought NFT</b> at a price higher than the specified (1-30 min. update)\n"

    if singular_buy + birds_buy + items_buy != 0:
        msg += "\n<b>Current <b>Buy</b> thresholds:</b>\n"
        if singular_buy > 0:
            msg += f"?<b>Singular</b> NFT > <b>{singular_buy:.2f} KSM</b> /singular_buy ❌\n"
        if birds_buy > 0:
            msg += f"?<b>Kanaria Bird</b> NFT > <b>{birds_buy:.2f} KSM</b> /birds_buy ❌\n"
        if items_buy > 0:
            msg += f"?<b>Kanaria Item</b> NFT > <b>{items_buy:.2f} KSM</b> /items_buy ❌\n"
    msg += "\nSingular NFT Buy:\n"
    msg += "/singular_buy_1 - 1 KSM\n"
    msg += "/singular_buy_5 - 5 KSM\n"
    msg += "/singular_buy_n - n KSM\n"
    msg += "\nKanaria Bird NFT Buy:\n"
    msg += "/birds_buy_3 - 3 KSM\n"
    msg += "/birds_buy_10 - 10 KSM\n"
    msg += "/birds_buy_n - n KSM\n"
    msg += "\nKanaria Item NFT Buy:\n"
    msg += "/items_buy_1 - 1 KSM\n"
    msg += "/items_buy_5 - 5 KSM\n"
    msg += "/items_buy_n - n KSM\n"

    msg += "\nAll Kanaria sales @kanariasales\n"
    msg += "All Singular sales @singularsales\n"
    msg += "Daily/weekly/monthly record sales @RMRKtopSales (new day starts at 00:00:00 UTC)\n"
    return msg


def parse_forsale_message(conn, bot, db, user_id, mt, parsed_val, msg):
    db.execute(f'SELECT * FROM tg_forsale WHERE user_id = {user_id}')
    birds_forsale = {}
    items_forsale = {}
    birds_forsale['any'], birds_forsale['limited'], birds_forsale['rare'], birds_forsale['super'], birds_forsale['founder'], items_forsale['any'], items_forsale[
        'legendary'], items_forsale['epic'], items_forsale['rare'], items_forsale['uncommon'], items_forsale['common'] = [Decimal(x) for x in db.fetchone()[1:]]
    mt = mt.lower()
    nft_type = 'any'
    if '/birds_forsale' in mt:
        if 'limited' in mt:
            nft_type = 'limited'
        elif 'rare' in mt:
            nft_type = 'rare'
        elif 'super' in mt:
            nft_type = 'super'
        elif 'founder' in mt:
            nft_type = 'founder'
        birds_forsale[nft_type] = parsed_val
        db.execute(
            f"UPDATE tg_forsale set birds_forsale_{nft_type}={birds_forsale[nft_type]} WHERE user_id = {user_id}")
        conn.commit()
    if '/items_forsale' in mt:
        if 'legendary' in mt:
            nft_type = 'legendary'
        elif 'epic' in mt:
            nft_type = 'epic'
        elif 'rare' in mt:
            nft_type = 'rare'
        elif 'uncommon' in mt:
            nft_type = 'uncommon'
        elif 'common' in mt:
            nft_type = 'common'
        items_forsale[nft_type] = parsed_val
        db.execute(
            f"UPDATE tg_forsale set items_forsale_{nft_type}={items_forsale[nft_type]} WHERE user_id = {user_id}")
        conn.commit()
    msg += "Bot will send a notification if someone listed <b>NFT for sale</b> at a price lower than the specified (1-30 min. update)\n"

    if sum([birds_forsale[x] for x in birds_forsale]) != 0:
        msg += "\nKanaria <b>Birds</b> thresholds:\n"
        if birds_forsale['any'] > 0:
            msg += f"?<b>Kanaria Any</b> NFT &lt; <b>{birds_forsale['any']:.2f} KSM</b> /birds_forsale_any ❌\n"
        if birds_forsale['super'] > 0:
            msg += f"?<b>Kanaria Super Founder</b> NFT &lt; <b>{birds_forsale['super']:.2f} KSM</b> /birds_forsale_super ❌\n"
        if birds_forsale['founder'] > 0:
            msg += f"?<b>Kanaria Founder</b> NFT &lt; <b>{birds_forsale['founder']:.2f} KSM</b> /birds_forsale_founder ❌\n"
        if birds_forsale['rare'] > 0:
            msg += f"?<b>Kanaria Rare</b> NFT &lt; <b>{birds_forsale['rare']:.2f} KSM</b> /birds_forsale_rare ❌\n"
        if birds_forsale['limited'] > 0:
            msg += f"?<b>Kanaria LE</b> NFT &lt; <b>{birds_forsale['limited']:.2f} KSM</b> /birds_forsale_limited ❌\n"

    if sum([items_forsale[x] for x in items_forsale]) != 0:
        msg += "\nKanaria <b>Items</b> thresholds:\n"
        if items_forsale['any'] > 0:
            msg += f"?<b>Kanaria Any</b> NFT &lt; <b>{items_forsale['any']:.2f} KSM</b> /items_forsale_any ❌\n"
        if items_forsale['legendary'] > 0:
            msg += f"?<b>Kanaria Legendary</b> NFT &lt; <b>{items_forsale['legendary']:.2f} KSM</b> /items_forsale_legendary ❌\n"
        if items_forsale['epic'] > 0:
            msg += f"?<b>Kanaria Epic</b> NFT &lt; <b>{items_forsale['epic']:.2f} KSM</b> /items_forsale_epic ❌\n"
        if items_forsale['rare'] > 0:
            msg += f"?<b>Kanaria Rare</b> NFT &lt; <b>{items_forsale['rare']:.2f} KSM</b> /items_forsale_rare ❌\n"
        if items_forsale['uncommon'] > 0:
            msg += f"?<b>Kanaria Uncommon</b> NFT &lt; <b>{items_forsale['uncommon']:.2f} KSM</b> /items_forsale_uncommon ❌\n"
        if items_forsale['common'] > 0:
            msg += f"?<b>Kanaria Common</b> NFT &lt; <b>{items_forsale['common']:.2f} KSM</b> /items_forsale_common ❌\n"

    msg += "\n<b>Kanaria Bird NFT For sale:</b>\n"
    msg += "/birds_forsale_any_10 &lt; 10 KSM Any birds\n"
    msg += "/birds_forsale_founder_300 &lt; 300 KSM Founder birds\n"
    msg += "/birds_forsale_rare_50 &lt; 50 KSM Rare birds\n"
    msg += "/birds_forsale_limited_10 &lt; 10 KSM Limited Edition birds\n"
    msg += "<b>Format:</b>\n"
    msg += "/birds_forsale_[super or founder or rare or limited]_n &lt; n KSM\n"
    msg += "\n<b>Kanaria Item NFT For sale:</b>\n"
    msg += "/items_forsale_any_5 &lt; 5 KSM Any items\n"
    msg += "/items_forsale_legendary_15 &lt; 15 KSM Legendary items\n"
    msg += "/items_forsale_epic_2 &lt; 2 KSM Epic items\n"
    msg += "/items_forsale_rare_1 &lt; 1 KSM Rare items\n"
    msg += "/items_forsale_common_1 &lt; 1 KSM Common items\n"
    msg += "<b>Format:</b>\n"
    msg += "/items_forsale_[legendary or epic or rare or uncommon or common or any]_n &lt; n KSM\n"
    return msg
