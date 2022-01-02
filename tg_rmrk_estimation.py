import re
from tg_rmrk_collections import *
from tg_rmrk_datatools import to_ksm
from tg_rmrk_config import *
from decimal import Decimal

# Find twin birds


def find_twin_birds(db, nft_id):
    db.execute(
        f"SELECT t2.nft_id FROM tg_birds_info t1, tg_birds_info t2 WHERE t1.nft_id = '{nft_id}' AND t1.nft_id != t2.nft_id AND t1.rarity = t2.rarity AND t1.theme = t2.theme AND t1.head = t2.head AND t1.eyes = t2.eyes AND t1.body = t2.body AND t1.tail = t2.tail AND t1.wingleft = t2.wingleft AND t1.wingright = t2.wingright AND t1.feet = t2.feet AND t1.resource_amount = t2.resource_amount;")
    twin_birds = {}
    if db.rowcount > 0:
        for twin_nft_id in db.fetchall():
            db.execute(
                f"SELECT sn::int from nfts_v2 where id = '{twin_nft_id[0]}';")
            twin_birds[db.fetchone()[0]] = twin_nft_id[0]
    return twin_birds

# Item price estimation


def estimate_item(db, nft_rarity, nft_type, nft_name):
    nft_name = nft_name.replace("'", "''")
    db.execute(
        f"SELECT old::bigint FROM nft_changes_v2 WHERE optype = 'BUY' AND field='forsale' AND nft_id IN (SELECT nft_id FROM tg_items_info WHERE rarity = '{nft_rarity}' AND type = '{nft_type}') ORDER BY block DESC limit 20;")
    if db.rowcount > 0:
        rarity_type_prices = [x[0] for x in db.fetchall()]
        rarity_type_prices_min, rarity_type_prices_max = to_ksm(
            min(rarity_type_prices)), to_ksm(max(rarity_type_prices))
        rarity_type_prices_avg = to_ksm(
            sum(rarity_type_prices) /
            len(rarity_type_prices))
    else:
        rarity_type_prices_min, rarity_type_prices_max, rarity_type_prices_avg = 0, 0, 0
    db.execute(
        f"SELECT old::bigint FROM nft_changes_v2 WHERE optype = 'BUY' AND field='forsale' AND nft_id IN (SELECT nft_id FROM tg_items_info WHERE rarity = '{nft_rarity}' AND type = '{nft_type}' AND name = '{nft_name}') ORDER BY block DESC limit 5;")
    if db.rowcount > 0:
        rarity_type_name_prices = [x[0] for x in db.fetchall()]
        rarity_type_name_prices_min, rarity_type_name_prices_max = to_ksm(
            min(rarity_type_name_prices)), to_ksm(max(rarity_type_name_prices))
        rarity_type_name_prices_avg = to_ksm(
            sum(rarity_type_name_prices) /
            len(rarity_type_name_prices))
    else:
        rarity_type_name_prices_min, rarity_type_name_prices_max, rarity_type_name_prices_avg = 0, 0, 0
    send_text = ""
    if rarity_type_name_prices_min > 0.0:
        send_text += "\n<b>Estimate by type, rarity and name</b>:\n"
        send_text += f"Min: <b>{rarity_type_name_prices_min:.2f}</b> KSM\n"
        send_text += f"Avg: <b>{rarity_type_name_prices_avg:.2f}</b> KSM\n"
        send_text += f"Max: <b>{rarity_type_name_prices_max:.2f}</b> KSM\n"
    if rarity_type_prices_min > 0.0:
        send_text += "\n<b>Estimate by type and rarity</b>:\n"
        send_text += f"Min: <b>{rarity_type_prices_min:.2f}</b> KSM\n"
        send_text += f"Avg: <b>{rarity_type_prices_avg:.2f}</b> KSM\n"
        send_text += f"Max: <b>{rarity_type_prices_max:.2f}</b> KSM\n"
    else:
        send_text += "Not enough statistics to Estimate. Try later\n"
    return send_text, rarity_type_prices_min, rarity_type_prices_max, rarity_type_prices_avg, rarity_type_name_prices_min, rarity_type_name_prices_max, rarity_type_name_prices_avg

# Get items for a Bird on specified block id


def bird_items_on_chain_block(db, nft_id, items_type, block=-1):
    if items_type == 'gems':
        items_type_ids_str = kanaria_gems_ids_str
    elif items_type == 'items':
        items_type_ids_str = kanaria_items_ids_str
    db.execute(
        f"SELECT id FROM nft_children_v2 WHERE nft_id='{nft_id}' AND id IN (SELECT id FROM nfts_v2 WHERE collection IN ('{items_type_ids_str}') AND burned!='true');")
    current_items = [x[0] for x in db.fetchall()]
    if block != -1:
        db.execute(
            f"SELECT nft_id, old, new FROM nft_changes_v2 WHERE optype='SEND' AND field='owner' AND (old='{nft_id}' OR new='{nft_id}') AND block >= {block} AND nft_id IN (SELECT id FROM nfts_v2 WHERE collection IN ('{items_type_ids_str}') AND burned!='true') ORDER BY block DESC;")
        nft_changes = db.fetchall()
        for nft_change in nft_changes:
            if nft_change[2] == nft_id:
                if nft_change[0] in current_items:
                    current_items.remove(nft_change[0])
            else:
                current_items.append(nft_change[0])
    return current_items

# Bird price estimation


def estimate_bird(db, nft_id, estimation_type="full", block=-1):
    send_text = ""
    total_birds_min, total_items_min, total_birds_max, total_items_max, total_birds_avg, total_items_avg = 0, 0, 0, 0, 0, 0
    db.execute(f"SELECT * FROM tg_birds_gems_info WHERE bird_id = '{nft_id}';")
    if db.rowcount > 0:
        bird_gems_info = db.fetchone()
        db.execute(f"SELECT * FROM tg_birds_info WHERE nft_id = '{nft_id}';")
        bird_info = list(db.fetchone())
        db.execute(
            f"SELECT * FROM tg_birds_traits_amount WHERE nft_id = '{nft_id}';")
        bird_trait_info = db.fetchone()
        db.execute(
            f"SELECT * FROM tg_birds_common_rate WHERE nft_id = '{nft_id}';")
        bird_total_info = db.fetchone()
        db.execute(f"SELECT count(*) FROM tg_birds_info;")
        len_birds_info = db.fetchone()[0]
        db.execute(f"SELECT sn::int from nfts_v2 where id = '{nft_id}';")
        serial_number = db.fetchone()[0]
        for i in range(2, len(bird_info[:-3])):
            if re.sub(r"[^0-9a-f-]", "", bird_info[i]) == bird_info[i]:
                bird_info[i] = ''.join([chr(int(x, 16))
                                       for x in bird_info[i].split('-')])

        # Show traits info
        if estimation_type in ("header", "full", "channel"):
            if bird_info[6][:3] != 'var':
                send_text += f"<b>⭐️Fullset: </b>{bird_info[6]} <b>{100.0 *bird_trait_info[5]/len_birds_info:.2f}%</b>\n"
            send_text += f"<b>Rarity: </b>{bird_info[1]} <b>{100.0 * bird_trait_info[1]/len_birds_info:.2f}%</b>\n<b>Theme: </b>{bird_info[2]} <b>{100.0 *bird_trait_info[2]/len_birds_info:.2f}%</b>\n"
            send_text += f"<b>Head: </b>{bird_info[4]} <b>{100.0 *bird_trait_info[3]/len_birds_info:.2f}%</b>\n<b>Eyes: </b>{bird_info[5]} <b>{100.0 *bird_trait_info[4]/len_birds_info:.2f}%</b>\n"
            send_text += f"<b>Body: </b>{bird_info[6]} <b>{100.0 *bird_trait_info[5]/len_birds_info:.2f}%</b>\n<b>Tail: </b>{bird_info[7]} <b>{100.0 *bird_trait_info[6]/len_birds_info:.2f}%</b>\n"
            send_text += f"<b>Wing left: </b>{bird_info[8]} <b>{100.0 *bird_trait_info[7]/len_birds_info:.2f}%</b>\n<b>Wing right: </b>{bird_info[9]} <b>{100.0 *bird_trait_info[8]/len_birds_info:.2f}%</b>\n"
            send_text += f"<b>Feet: </b>{bird_info[10]} <b>{100.0 *bird_trait_info[9]/len_birds_info:.2f}%</b>\n<b>Resources: </b>{bird_info[11]} <b>{100.0 *bird_trait_info[10]/len_birds_info:.2f}%</b>\n"

        # Show scores info
        if estimation_type in ("full", "channel"):
            send_text += f"\n<b>Bird score: </b>{bird_info[12]:.2f}\n"
            send_text += f"<b>Gems score: </b>{bird_gems_info[2]:.2f}\n"
            send_text += f"<b>Total score: </b>{bird_total_info[1]:.2f}\n<b>Total place: {bird_total_info[2]}</b>/{len_birds_info}\n"
        send_text = send_text.replace(
            'var0',
            'iridescent').replace(
            'var1',
            'plain').replace(
            'var2',
            'pinstrip').replace(
                'var3',
                'speckled').replace(
                    'var4',
            'solid')

        # Calculate Bird + gems price
        if estimation_type != "header":
            send_text += f"\n<b>Estimate Bird + Gems price: </b>\n"
            not_enough = False
            # Similar birds = Birds with score +/- 5%
            db.execute(
                f"SELECT nft_id, block, old::bigint FROM nft_changes_v2 WHERE optype='BUY' AND field='forsale' AND nft_id IN (SELECT nft_id FROM tg_birds_common_rate WHERE trait_score BETWEEN {bird_total_info[1]*0.95} AND {bird_total_info[1]*1.05}) ORDER BY block DESC LIMIT 10;")
            if db.rowcount == 0:
                # Similar birds = Birds with score +/- 10%
                db.execute(
                    f"SELECT nft_id, block, old::bigint FROM nft_changes_v2 WHERE optype='BUY' AND field='forsale' AND nft_id IN (SELECT nft_id FROM tg_birds_common_rate WHERE trait_score BETWEEN {bird_total_info[1]*0.9} AND {bird_total_info[1]*1.1}) ORDER BY block DESC LIMIT 10;")
                if db.rowcount == 0:
                    not_enough = True

            # Calculate prices for similar birds items
            if not not_enough:
                similar_birds_sold = db.fetchall()
                similar_birds_prices = []
                for similar_bird_sold in similar_birds_sold:
                    similar_bird_items = bird_items_on_chain_block(
                        db, similar_bird_sold[0], 'items', similar_bird_sold[1])
                    similar_total_items_prices = []
                    for item_id in similar_bird_items:
                        db.execute(
                            f"SELECT rarity, type, name FROM tg_items_info WHERE nft_id = '{item_id}';")
                        item_rarity, item_type, item_name = db.fetchone()
                        prices = estimate_item(
                            db, item_rarity, item_type, item_name)[1:4]
                        similar_total_items_prices.append(prices)
                    similar_bird_max, similar_bird_min, similar_bird_avg = to_ksm(similar_bird_sold[2]) - sum([x[0] for x in similar_total_items_prices]), to_ksm(
                        similar_bird_sold[2]) - sum([x[1] for x in similar_total_items_prices]), to_ksm(similar_bird_sold[2]) - sum([x[2] for x in similar_total_items_prices])
                    if similar_bird_min > 1:
                        similar_birds_prices.append(
                            [similar_bird_min, similar_bird_avg, similar_bird_max])
                if similar_birds_prices:
                    total_birds_min, total_birds_avg, total_birds_max = min([x[0] for x in similar_birds_prices]), sum(
                        [x[1] for x in similar_birds_prices]) / len(similar_birds_prices), max([x[2] for x in similar_birds_prices])
                    send_text += f"Min: <b>{total_birds_min:.2f}</b> KSM\n"
                    send_text += f"Avg: <b>{total_birds_avg:.2f}</b> KSM\n"
                    send_text += f"Max: <b>{total_birds_max:.2f}</b> KSM\n"
                else:
                    not_enough = True
            if not_enough:
                send_text += "Not enough statistics for similar birds\n"

            # Calculate price of all bird items
            send_text += f"\n<b>Estimate Items price: </b>\n"
            items_ids = bird_items_on_chain_block(db, nft_id, 'items', block)
            total_items_prices = []
            for item_id in items_ids:
                db.execute(
                    f"SELECT rarity, type, name FROM tg_items_info WHERE nft_id = '{item_id}';")
                item_rarity, item_type, item_name = db.fetchone()
                prices = estimate_item(
                    db, item_rarity, item_type, item_name)[1:4]
                if prices == (0, 0, 0):
                    item_name = item_name.replace("'", "''")
                    send_text += f"Can't estimate <a href='{kanaria_market_url}{item_id}'>{item_name}</a>\n"
                total_items_prices.append(prices)
            total_items_min, total_items_max, total_items_avg = sum([x[0] for x in total_items_prices]), sum(
                [x[1] for x in total_items_prices]), sum([x[2] for x in total_items_prices])
            send_text += f"Min: <b>{total_items_min:.2f}</b> KSM\n"
            send_text += f"Avg: <b>{total_items_avg:.2f}</b> KSM\n"
            send_text += f"Max: <b>{total_items_max:.2f}</b> KSM\n"
            send_text += f"\n<b>Estimate Total price: </b>\n"

            # Total Bird + gems + items price
            if not_enough:
                send_text += "Not enough statistics for similar birds\n"
            else:
                send_text += f"Min: <b>{total_birds_min + total_items_min:.2f}</b> KSM\n"
                send_text += f"Avg: <b>{total_birds_avg + total_items_avg:.2f}</b> KSM\n"
                send_text += f"Max: <b>{total_birds_max + total_items_max:.2f}</b> KSM\n"

        if estimation_type not in ("header", "channel"):
            send_text += f"<a href='{kanaria_market_url}{nft_id}'>Bird_{serial_number}</a>\n"
        if estimation_type not in ("short", "channel"):
            send_text += f"/estimate_{serial_number}\n"
        if estimation_type not in ("full", "channel"):
            send_text += f"/estimate_full_{serial_number}\n"

        twin_birds = find_twin_birds(db, nft_id)
        if twin_birds and estimation_type != "header":
            send_text += f"\n<b>Twins:</b>\n"
            for twin_bird in twin_birds:
                send_text += f"<a href='{kanaria_market_url}{twin_birds[twin_bird]}'>Bird_{twin_bird}</a> "
                if estimation_type != "channel":
                    send_text += f"/estimate_full_{twin_bird}"
                send_text += '\n'

    return send_text, total_birds_min, total_birds_max, serial_number

# Wallet price estimation

def estimate_wallet(db, address, estimation_type='short'):
    send_text = ""
    total_wallet_min, total_wallet_max = 0, 0
    total_birds_min, total_birds_max = 0, 0
    total_items_min, total_items_max = 0, 0
    db.execute(
            f"SELECT 1 WHERE '{address}' in (SELECT rootowner FROM (SELECT rootowner,count(*) c FROM nfts_v2 WHERE id LIKE '%KANBIRD%' GROUP BY rootowner ORDER BY c DESC LIMIT 20) AS t1);")
    if db.rowcount > 0:
        send_text += "This wallet in TOP 20. Please don't do that, it can make our bot suffer.\n"
        return send_text, total_wallet_min, total_wallet_max

    db.execute("SELECT * FROM tg_ksm_exchange_rate")
    ksm_exchange_rate = db.fetchone()[0]
    
    #Estimate Birds
    db.execute(
            f"SELECT id FROM nfts_v2 WHERE rootowner='{address}' AND collection IN ('{kanaria_birds_ids_str}') AND burned!='true';")
    if db.rowcount > 0:
        send_text += "<b>Birds + Gems:</b>\n"
        wallet_birds = db.fetchall()
        for wallet_bird in wallet_birds:
            bird_min, bird_max, bird_sn = estimate_bird(db, wallet_bird[0])[1:]
            total_birds_min += bird_min
            total_birds_max += bird_max
            if estimation_type=='full':
                send_text += f"<a href='{kanaria_market_url}{wallet_bird[0]}'>Bird_{bird_sn}</a> {bird_min:.2f} - {bird_max:.2f} KSM\n"
        send_text += f"Min: <b>{total_birds_min:.2f}</b> (~{Decimal(total_birds_min) * Decimal(ksm_exchange_rate):.2f}$) Max <b>{total_birds_max:.2f}</b> (~{Decimal(total_birds_max) * Decimal(ksm_exchange_rate):.2f}$) KSM\n"
    
    #Estimate Items
    db.execute(
            f"SELECT id FROM nfts_v2 WHERE rootowner='{address}' AND collection IN ('{kanaria_items_ids_str}') AND burned!='true';")
    if db.rowcount > 0:
        send_text += "\n<b>Items:</b>\n"
        wallet_items = db.fetchall()
        for wallet_item in wallet_items:
            db.execute(
                    f"SELECT rarity, type, name FROM tg_items_info WHERE nft_id = '{wallet_item[0]}';")
            item_rarity, item_type, item_name = db.fetchone()
            item_min, item_max = estimate_item(
                db, item_rarity, item_type, item_name)[1:3]
            total_items_min += item_min
            total_items_max += item_max
            if estimation_type=='full':
                item_name = item_name.replace("'", "''")
                if total_items_min > 0:
                    send_text += f"<a href='{kanaria_market_url}{wallet_item[0]}'>{item_name}</a> {item_min:.2f} - {item_max:.2f} KSM\n"
                else:
                    send_text += f"<a href='{kanaria_market_url}{wallet_item[0]}'>{item_name}</a> Can't estimate\n"
        send_text += f"Min: <b>{total_items_min:.2f}</b> (~{Decimal(total_items_min) * Decimal(ksm_exchange_rate):.2f}$) Max <b>{total_items_max:.2f}</b> (~{Decimal(total_items_max) * Decimal(ksm_exchange_rate):.2f}$) KSM\n"
    total_wallet_min, total_wallet_max = total_birds_min + total_items_min, total_birds_max + total_birds_max
    send_text += "\n<b>Total:</b>\n"
    send_text += f"Min: <b>{total_wallet_min:.2f}</b> (~{Decimal(total_wallet_min) * Decimal(ksm_exchange_rate):.2f}$) Max <b>{total_wallet_max:.2f}</b> (~{Decimal(total_wallet_max) * Decimal(ksm_exchange_rate):.2f}$) KSM\n"
    
    send_text += f"\n<a href='{sub_id_url}{address}'>Sub ID</a> | <a href='{kanaria_nest_url}{address}'>Kanaria</a>\n"
    if estimation_type != 'full':
        send_text += f'/estimate_full_{address}'
    else:
        send_text += f'/estimate_{address}'
    if len(send_text) >= 4096:
        send_text = f"The message is too long, please use a shorter version:\n/estimate_{address}"

    return send_text, total_wallet_min, total_wallet_max
