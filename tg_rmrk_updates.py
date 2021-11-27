import psycopg2
import time
import datetime
import json
from tg_rmrk_datatools import *
from tg_rmrk_send_message import *
from tg_rmrk_collections import *
from tg_rmrk_estimation import *
from tg_rmrk_config import *

#Collect changed birds to update their images info
def update_changed_birds(conn, db,tg_lastblock_v1, tg_lastblock_v2):
    birds_changes_sql=f'''SELECT DISTINCT(old) FROM nft_changes_v2 WHERE optype = 'SEND' AND field = 'owner' AND block > {tg_lastblock_v2} AND old IN (SELECT id FROM nfts_v2 WHERE collection IN ('{kanaria_birds_ids_str}'))
UNION
SELECT DISTINCT(new) FROM nft_changes_v2 WHERE optype = 'SEND' AND field = 'owner' AND block > {tg_lastblock_v2} AND new IN (SELECT id FROM nfts_v2 WHERE collection IN ('{kanaria_birds_ids_str}'));'''
    db.execute(birds_changes_sql)
    changed_birds_ids = list(set([x[0] for x in db.fetchall()]))
    changed_birds_ids_str = "','".join(changed_birds_ids)

    db.execute(f"DELETE FROM tg_nft_metadata WHERE nft_id in ('{changed_birds_ids_str}');")
    conn.commit()

    for changed_bird in changed_birds_ids:
        db.execute(f"SELECT metadata FROM nfts_v2 WHERE id = '{changed_bird}';")
        nft_metadata = fetch_metadata(db, changed_bird, db.fetchone()[0])

    db.execute(f"SELECT DISTINCT(owner) FROM nfts_v2 WHERE burned != '' AND collection IN ('{kanaria_gems_ids_str}') AND updatedatblock > {tg_lastblock_v2} AND owner IN (SELECT id FROM nfts_v2 WHERE collection IN ('{kanaria_birds_ids_str}'));")
    birds_with_burned_gems_ids = list(set([x[0] for x in db.fetchall()]))
    birds_with_burned_gems_ids_str = "','".join(birds_with_burned_gems_ids)
    db.execute(f"DELETE FROM tg_birds_gems_info WHERE bird_id in ('{birds_with_burned_gems_ids_str}');")
    conn.commit()

#Update traits, scores and estimation info for new birds, gems, items
def update_birds_gems_items(conn,db,tg_lastblock_v1, tg_lastblock_v2):
    # Collect trait info for new Birds to estimate
    db.execute(f"SELECT id, metadata FROM nfts_v2 WHERE burned!='true' AND collection IN ('{kanaria_birds_ids_str}') AND id NOT IN (SELECT nft_id FROM tg_birds_info) ORDER by id LIMIT 100;")
    new_birds = db.fetchall()
    for new_bird in new_birds:
        print(new_bird)
        nft_metadata = fetch_metadata(db, new_bird[0], new_bird[1])

        if 'properties' in nft_metadata:
            nft_rarity = nft_metadata['properties']['rarity']['value'].strip().lower()
            nft_theme = nft_metadata['properties'].get('theme',{'value':'Defaultyellow'})['value'].strip().lower()
            nft_name = nft_metadata.get('name','').replace("'","''")
        
        #Collect parts info
        db.execute(f"SELECT priority FROM nfts_v2 WHERE id = '{new_bird[0]}';")
        bird_resources = list(db.fetchone()[0])
        bird_resources_str = "','".join(bird_resources)
        db.execute(f"SELECT parts FROM nft_resources_v2 WHERE id IN ('{bird_resources_str}');")
        
        bird_resources_parts = [x[0] for x in db.fetchall()]
        bird_parts_dict = {}
        for bird_resource_parts in bird_resources_parts:
            for bird_resource_part in bird_resource_parts:
                if "top_rare" in bird_resource_part or "tail_rare" in bird_resource_part:
                    bird_parts_dict['tail'] = bird_resource_part.split("_")[0].lower()
                    bird_parts_dict['feet'] = bird_parts_dict['tail']
                elif "_" in bird_resource_part:
                    bird_part_value, bird_part_type = [x.lower() for x in bird_resource_part.split("_")]
                    if bird_part_type in ("head", "eyes", "body", "tail", "wingleft", "wingright", "footleft"):
                        if not bird_parts_dict.get(bird_part_type,""):
                            bird_parts_dict[bird_part_type] = bird_part_value

        print(bird_parts_dict)
        db.execute(f"INSERT INTO tg_birds_info(nft_id, rarity, theme, name, head, eyes, body, tail, wingleft, wingright, feet, resource_amount, trait_score, trait_place) VALUES('{new_bird[0]}', '{nft_rarity}','{nft_theme}','{nft_name}','{bird_parts_dict['head']}','{bird_parts_dict['eyes']}','{bird_parts_dict['body']}','{bird_parts_dict['tail']}','{bird_parts_dict['wingleft']}','{bird_parts_dict['wingright']}','{bird_parts_dict['footleft']}',{len(bird_resources)},0,0);")
    conn.commit()

    #Update bird trait scores and places
    db.execute(f"SELECT * FROM tg_birds_info WHERE trait_score = 0;")
    if db.rowcount > 0:
        db.execute(f"SELECT * FROM tg_birds_info;")
        birds_traits_info = db.fetchall()
        total_birds = 0.0
        total_birds_dict = {}
        birds_score_dict = {}
        for trait_type in ('rarity', 'theme', 'head', 'eyes', 'body', 'tail', 'wingleft', 'wingright', 'feet', 'resource_amount'):
            total_birds_dict[trait_type] = {}
        
        #Calculate trait amounts
        for bird_traits_info in birds_traits_info:
            nft_id, nft_rarity, nft_theme, nft_name, nft_head, nft_eyes, nft_body, nft_tail, nft_wingleft, nft_wingright, nft_feet, nft_resource_amount, nft_trait_score, nft_trait_place = bird_traits_info
            total_birds += 1
            total_birds_dict['rarity'][nft_rarity] = total_birds_dict['rarity'].get(nft_rarity, 0) + 1
            total_birds_dict['theme'][nft_theme] = total_birds_dict['theme'].get(nft_theme, 0) + 1
            total_birds_dict['head'][nft_head] = total_birds_dict['head'].get(nft_head, 0) + 1
            total_birds_dict['eyes'][nft_eyes] = total_birds_dict['eyes'].get(nft_eyes, 0) + 1
            total_birds_dict['body'][nft_body] = total_birds_dict['body'].get(nft_body, 0) + 1
            total_birds_dict['tail'][nft_tail] = total_birds_dict['tail'].get(nft_tail, 0) + 1
            total_birds_dict['wingleft'][nft_wingleft] = total_birds_dict['wingleft'].get(nft_wingleft, 0) + 1
            total_birds_dict['wingright'][nft_wingright] = total_birds_dict['wingright'].get(nft_wingright, 0) + 1
            total_birds_dict['feet'][nft_feet] = total_birds_dict['feet'].get(nft_feet, 0) + 1
            total_birds_dict['resource_amount'][nft_resource_amount] = total_birds_dict['resource_amount'].get(nft_resource_amount, 0) + 1
        
        #Calculate trait scores
        for bird_traits_info in birds_traits_info:
            nft_id, nft_rarity, nft_theme, nft_name, nft_head, nft_eyes, nft_body, nft_tail, nft_wingleft, nft_wingright, nft_feet, nft_resource_amount, nft_trait_score, nft_trait_place = bird_traits_info
            birds_score_dict[nft_id] = 2 * total_birds / total_birds_dict['rarity'][nft_rarity]
            birds_score_dict[nft_id] += 1 * total_birds / total_birds_dict['theme'][nft_theme]
            birds_score_dict[nft_id] += 1 * total_birds / total_birds_dict['head'][nft_head]
            birds_score_dict[nft_id] += 1 * total_birds / total_birds_dict['eyes'][nft_eyes]
            birds_score_dict[nft_id] += 3 * total_birds / total_birds_dict['body'][nft_body]
            birds_score_dict[nft_id] += 1 * total_birds / total_birds_dict['tail'][nft_tail]
            birds_score_dict[nft_id] += 1 * total_birds / total_birds_dict['wingleft'][nft_wingleft]
            birds_score_dict[nft_id] += 1 * total_birds / total_birds_dict['wingright'][nft_wingright]
            birds_score_dict[nft_id] += 1 * total_birds / total_birds_dict['feet'][nft_feet]
            birds_score_dict[nft_id] += 3 * total_birds / total_birds_dict['resource_amount'][nft_resource_amount]
            if birds_score_dict[nft_id] == 0:
                birds_score_dict[nft_id] = -1
            db.execute(f"INSERT INTO tg_birds_traits_amount(nft_id, rarity, theme, head, eyes, body, tail, wingleft, wingright, feet, resource_amount) VALUES('{nft_id}',{total_birds_dict['rarity'][nft_rarity]},{total_birds_dict['theme'][nft_theme]},{total_birds_dict['head'][nft_head]}, {total_birds_dict['eyes'][nft_eyes]},{total_birds_dict['body'][nft_body]},{total_birds_dict['tail'][nft_tail]},{total_birds_dict['wingleft'][nft_wingleft]},{total_birds_dict['wingright'][nft_wingright]},{total_birds_dict['feet'][nft_feet]},{total_birds_dict['resource_amount'][nft_resource_amount]}) ON CONFLICT (nft_id) DO UPDATE SET rarity = excluded.rarity, theme = excluded.theme, head = excluded.head, eyes = excluded.eyes, body = excluded.body, tail = excluded.tail, wingleft = excluded.wingleft, wingright = excluded.wingright, feet = excluded.feet, resource_amount = excluded.resource_amount;")
        top_place = 0
        for bird_id in sorted(birds_score_dict, key=birds_score_dict.get, reverse=True):
            top_place += 1
            db.execute(f"UPDATE tg_birds_info set trait_score = {birds_score_dict[bird_id]:.2f}, trait_place={top_place} WHERE nft_id='{bird_id}';")
        conn.commit()

    #Collect trait info for new Gems to estimate
    db.execute(f"SELECT nft_id FROM tg_birds_info WHERE nft_id NOT IN (SELECT bird_id FROM tg_birds_gems_info);")
    new_birds_with_gems = [x[0] for x in db.fetchall()]
    for new_bird_with_gems in new_birds_with_gems:
        bird_gems_ids = bird_items_on_chain_block(db, new_bird_with_gems, 'gems', lastblock_v2)
        db.execute(f"INSERT INTO tg_birds_gems_info(bird_id, gems, trait_score, trait_place) VALUES('{new_bird_with_gems}', '{json.dumps(bird_gems_ids)}',0,0);")
    conn.commit()

    #Update gem trait scores and places for birds
    db.execute(f"SELECT * FROM tg_birds_gems_info WHERE trait_score = 0;")
    if db.rowcount > 0:
        db.execute(f"SELECT * FROM tg_birds_gems_info;")
        birds_gems_info = db.fetchall()
        total_gems = 0.0
        total_gems_dict = {}
        gems_score_dict = {}
        for bird_gems_info in birds_gems_info:
            for gem_id in bird_gems_info[1]:
                total_gems += 1
                db.execute(f"SELECT collection FROM nfts_v2 WHERE id = '{gem_id}';")
                gem_collection = db.fetchone()[0]
                total_gems_dict[gem_collection] = total_gems_dict.get(gem_collection, 0) + 1
        for bird_gems_info in birds_gems_info:
            gems_score_dict[bird_gems_info[0]] = 0
            for gem_id in bird_gems_info[1]:
                db.execute(f"SELECT collection FROM nfts_v2 WHERE id = '{gem_id}';")
                gem_collection = db.fetchone()[0]
                if 'KANGEMNRD' in gem_collection:
                    gems_score_dict[bird_gems_info[0]] += (10 * float(total_gems / total_gems_dict[gem_collection]))
                elif 'KANGEMBRGI' in gem_collection:
                    gems_score_dict[bird_gems_info[0]] += (3 * float(total_gems / total_gems_dict[gem_collection]))
                else:
                    gems_score_dict[bird_gems_info[0]] += float(total_gems / total_gems_dict[gem_collection])
            if gems_score_dict[bird_gems_info[0]] == 0:
                gems_score_dict[bird_gems_info[0]] = -1
        top_place = 0
        for bird_gems_id in sorted(gems_score_dict, key=gems_score_dict.get, reverse=True):
            top_place += 1
            db.execute(f"UPDATE tg_birds_gems_info set trait_score = {gems_score_dict[bird_gems_id]:.2f}, trait_place={top_place} WHERE bird_id='{bird_gems_id}';")
        conn.commit()
        db.execute("INSERT INTO tg_birds_common_rate (SELECT t1.nft_id, t1.trait_score + t2.trait_score, 0 FROM tg_birds_info t1, tg_birds_gems_info t2 WHERE t1.nft_id = t2.bird_id) ON CONFLICT (nft_id) DO UPDATE SET trait_score = excluded.trait_score, trait_place = excluded.trait_place;")
        conn.commit()
        db.execute("SELECT * FROM tg_birds_common_rate;")
        birds_common_rates = db.fetchall()
        birds_common_rates_dict = {}
        for bird_common_rates in birds_common_rates:
            birds_common_rates_dict[bird_common_rates[0]] = bird_common_rates[1]
        top_place = 0
        for bird_nft_id in sorted(birds_common_rates_dict, key=birds_common_rates_dict.get, reverse=True):
            top_place += 1
            db.execute(f"UPDATE tg_birds_common_rate set trait_place={top_place} WHERE nft_id='{bird_nft_id}';")
        conn.commit()

    #Collect info for new Items to estimate
    db.execute(f"SELECT id, metadata FROM nfts_v2 WHERE burned != 'true' AND (collection IN ('{kanaria_items_ids_str}') OR collection IN ('{kanaria_gems_ids_str}')) AND id NOT IN (SELECT nft_id FROM tg_items_info);")
    new_items = db.fetchall()
    for new_item in new_items:
        nft_metadata = fetch_metadata(db, new_item[0], new_item[1])
        if 'properties' in nft_metadata:
            nft_rarity = nft_metadata['properties']['rarity']['value'].strip().lower()
            nft_type = nft_metadata['properties']['type']['value'].strip().lower()
            nft_name = nft_metadata.get('name','').replace("'","''")
            db.execute(f"INSERT INTO tg_items_info(nft_id, rarity, type, name) VALUES('{new_item[0]}', '{nft_rarity}','{nft_type}','{nft_name}');")
            conn.commit()
        else:
            print(nft_metadata)
            print(new_item[0])

#Check daily, weekly and monthly records for records channel
def update_records(conn, db, bot, tg_lastblock_v1, tg_lastblock_v2):
    db.execute(f"SELECT * FROM tg_record;")
    records = {'daily':{}, 'weekly':{}, 'monthly':{}}
    for record in db.fetchall():
        records[record[0]][record[1]] = record[2:]
    today = datetime.date.today()
    to_send_records = {'bird':{}, 'item': {}, 'singular': {}}
    record_updated = False
    for period in records:
        if period == 'daily':
            comp_time = int(today.strftime("%s"))
        elif period == 'weekly':
            comp_time = int((today - datetime.timedelta(days=today.weekday())).strftime("%s"))
        else:
            comp_time = int((today - datetime.timedelta(days=today.day - 1)).strftime("%s"))

        db.execute(f"SELECT old::bigint, nft_id, block FROM nft_changes_v2 WHERE optype ='BUY' AND field='forsale' AND nft_id IN (SELECT id from nfts_v2 WHERE collection IN ('{kanaria_birds_ids_str}')) AND block >= (SELECT block FROM tg_block_history WHERE approx_time > {comp_time} ORDER BY block LIMIT 1) ORDER BY old::bigint DESC, block LIMIT 1;")
        if db.rowcount > 0:
            birds_record = db.fetchone()
            if records[period]['bird'][0] != birds_record[1] or records[period]['bird'][1] != birds_record[2]:
                db.execute(f"UPDATE tg_record SET nft_id = '{birds_record[1]}', block = {birds_record[2]} WHERE record_period = '{period}' AND record_type = 'bird';")
                to_send_records['bird'][period] = birds_record

        db.execute(f"SELECT old::bigint, nft_id, block FROM nft_changes_v2 WHERE optype ='BUY' AND field='forsale' AND nft_id IN (SELECT id from nfts_v2 WHERE collection IN ('{kanaria_items_ids_str}')) AND block >= (SELECT block FROM tg_block_history WHERE approx_time > {comp_time} ORDER BY block LIMIT 1) ORDER BY old::bigint DESC, block LIMIT 1;")
        if db.rowcount > 0:
            birds_record = db.fetchone()
            if records[period]['item'][0] != birds_record[1] or records[period]['item'][1] != birds_record[2]:
                db.execute(f"UPDATE tg_record SET nft_id = '{birds_record[1]}', block = {birds_record[2]} WHERE record_period = '{period}' AND record_type = 'item';")
                to_send_records['item'][period] = birds_record

        db.execute(f"SELECT old::bigint, nft_id, block FROM nft_changes_vlite WHERE optype ='BUY' AND field='forsale' AND block >= (SELECT block FROM tg_block_history WHERE approx_time > {comp_time} ORDER BY block LIMIT 1) ORDER BY old::bigint DESC, block LIMIT 1;")
        if db.rowcount > 0:
            birds_record = db.fetchone()
            if records[period]['singular'][0] != birds_record[1] or records[period]['singular'][1] != birds_record[2]:
                db.execute(f"UPDATE tg_record SET nft_id = '{birds_record[1]}', block = {birds_record[2]} WHERE record_period = '{period}' AND record_type = 'singular';")
                to_send_records['singular'][period] = birds_record
    conn.commit()

    for record_type in to_send_records:
        if 'monthly' in to_send_records[record_type]:
            send_record_message_to_channel(conn, bot, db, record_type, 'monthly', to_send_records[record_type]['monthly'])
        elif 'weekly' in to_send_records[record_type]:
            send_record_message_to_channel(conn, bot, db, record_type, 'weekly', to_send_records[record_type]['weekly'])
        elif 'daily' in to_send_records[record_type]:
            send_record_message_to_channel(conn, bot, db, record_type, 'daily', to_send_records[record_type]['daily'])

#Collect NFT changes
def update_nft_changes(conn,db,tg_lastblock_v1, tg_lastblock_v2):
    #Collect NFT updates
    changes_sql=f'''INSERT INTO tg_changes_messages 
(SELECT t3.user_id, t1.nft_id, t1.old, t1.new, t1.block as block, t1.field, t1.optype, t2.metadata, t3.nft_url, t3.version
FROM nft_changes_vlite t1, nfts_vlite t2, tg_follows t3, tg_users t4
WHERE  t1.block > {tg_lastblock_v1} AND t1.nft_id=t3.nft_id AND t3.version = 'v1' AND t1.nft_id=t2.id AND t3.user_id=t4.id AND t4.is_active
UNION
SELECT t3.user_id, t1.nft_id, t1.old, t1.new, t1.block as block, t1.field, t1.optype, t2.metadata, t3.nft_url, t3.version
FROM nft_changes_v2 t1, nfts_v2 t2, tg_follows t3, tg_users t4
WHERE  t1.block > {tg_lastblock_v2} AND t1.nft_id=t3.nft_id AND t3.version = 'v2' AND t1.nft_id=t2.id AND t3.user_id=t4.id AND t4.is_active ORDER BY block);'''
    db.execute(changes_sql)

    #Collect Sold NFTs
    db.execute(f"SELECT t1.nft_id, t1.old, t1.block, t2.metadata FROM nft_changes_vlite t1, nfts_vlite t2 WHERE  t1.block > {tg_lastblock_v1} AND t1.optype='BUY' AND t1.field='forsale' AND t1.nft_id=t2.id ORDER BY t1.block;")
    sold_list_singular = list(map(lambda x:[x[0], to_ksm(x[1], 'singular'), x[2], x[3]], db.fetchall()))
    db.execute(f"SELECT t1.nft_id, t1.old, t1.block, t2.metadata FROM nft_changes_v2 t1, nfts_v2 t2 WHERE  t1.block > {tg_lastblock_v2} AND t1.optype='BUY' AND t1.field='forsale' AND t1.nft_id=t2.id AND t2.collection IN ('{kanaria_birds_ids_str}') ORDER BY t1.block;")
    sold_list_birds = list(map(lambda x:[x[0], to_ksm(x[1]), x[2], x[3]], db.fetchall()))
    db.execute(f"SELECT t1.nft_id, t1.old, t1.block, t2.metadata FROM nft_changes_v2 t1, nfts_v2 t2 WHERE  t1.block > {tg_lastblock_v2} AND t1.optype='BUY' AND t1.field='forsale' AND t1.nft_id=t2.id AND t2.collection IN ('{kanaria_items_ids_str}') ORDER BY t1.block;")
    sold_list_items = list(map(lambda x:[x[0], to_ksm(x[1]), x[2], x[3]], db.fetchall()))
    db.execute("SELECT * FROM tg_buy WHERE user_id IN (SELECT id FROM tg_users WHERE is_active) and (singular_buy + birds_buy + items_buy) > 0;")
    users_sold_params = db.fetchall()
    users_sold_params_dict = {}
    sold_messages_list = []
    for user_sold_params in users_sold_params:
        users_sold_params_dict[user_sold_params[0]] = {'singular_buy': user_sold_params[1], 'birds_buy': user_sold_params[2], 'items_buy': user_sold_params[3]}
    for user_id in users_sold_params_dict:
        user_buy = users_sold_params_dict[user_id]
        if user_buy['singular_buy'] > 0.0:
            for sold in sold_list_singular:
                if sold[1] >= user_buy['singular_buy']:
                    sold_messages_list.append([user_id, 'singular', sold[0], sold[1], sold[2], sold[3]])
        if user_buy['birds_buy'] > 0.0:
            for sold in sold_list_birds:
                if sold[1] >= user_buy['birds_buy']:
                    sold_messages_list.append([user_id, 'bird', sold[0], sold[1], sold[2], sold[3]])
        if user_buy['items_buy'] > 0.0:
            for sold in sold_list_items:
                if sold[1] >= user_buy['items_buy']:
                    sold_messages_list.append([user_id, 'item', sold[0], sold[1], sold[2], sold[3]])
   
    for sold_message in sold_messages_list:
        db.execute(f"INSERT INTO tg_buy_messages(user_id, type, nft_id, price, block, metadata) VALUES ({sold_message[0]},'{sold_message[1]}','{sold_message[2]}',{sold_message[3]:.3f},{sold_message[4]},'{sold_message[5]}');")
    conn.commit()

    #Collect Listed NFTs
    db.execute(f"SELECT t1.nft_id, t1.new, t1.block, t2.metadata FROM nft_changes_v2 t1, nfts_v2 t2 WHERE  t1.block > {tg_lastblock_v2} AND t1.optype='LIST' AND t1.field='forsale' AND t1.nft_id=t2.id AND t1.new::bigint > 0.0 AND t2.collection IN ('{kanaria_birds_ids_str}') ORDER BY t1.block;")
    forsale_list_birds = list(map(lambda x:[x[0], to_ksm(x[1]), x[2], x[3]], db.fetchall()))
    db.execute(f"SELECT t1.nft_id, t1.new, t1.block, t2.metadata FROM nft_changes_v2 t1, nfts_v2 t2 WHERE  t1.block > {tg_lastblock_v2} AND t1.optype='LIST' AND t1.field='forsale' AND t1.nft_id=t2.id AND t1.new::bigint > 0.0 AND t2.collection IN ('{kanaria_items_ids_str}') ORDER BY t1.block;")
    forsale_list_items = list(map(lambda x:[x[0], to_ksm(x[1]), x[2], x[3]], db.fetchall()))
    db.execute("SELECT * FROM tg_forsale WHERE user_id IN (SELECT id FROM tg_users WHERE is_active) and (birds_forsale_any + birds_forsale_limited + birds_forsale_rare + birds_forsale_super + birds_forsale_founder + items_forsale_any + items_forsale_legendary + items_forsale_epic + items_forsale_rare +items_forsale_uncommon +items_forsale_common) > 0;")
    users_forsale_params = db.fetchall()
    birds_forsale_by_user = {}
    items_forsale_by_user = {}
    forsale_messages_list = []
    for user_forsale_params in users_forsale_params:
        birds_forsale_by_user[user_forsale_params[0]] = {}
        items_forsale_by_user[user_forsale_params[0]] = {}
        birds_forsale_by_user[user_forsale_params[0]]['any'], birds_forsale_by_user[user_forsale_params[0]]['limited'], birds_forsale_by_user[user_forsale_params[0]]['rare'], birds_forsale_by_user[user_forsale_params[0]]['super'], birds_forsale_by_user[user_forsale_params[0]]['founder'], items_forsale_by_user[user_forsale_params[0]]['any'], items_forsale_by_user[user_forsale_params[0]]['legendary'], items_forsale_by_user[user_forsale_params[0]]['epic'], items_forsale_by_user[user_forsale_params[0]]['rare'], items_forsale_by_user[user_forsale_params[0]]['uncommon'], items_forsale_by_user[user_forsale_params[0]]['common'] = [Decimal(x) for x in user_forsale_params[1:]]
    for forsale in forsale_list_birds:
        for user_id in birds_forsale_by_user:
            birds_forsale = birds_forsale_by_user[user_id]
            if birds_forsale['any'] >= forsale[1]:
                forsale_messages_list.append([user_id, 'bird', 'any', forsale[0], forsale[1], forsale[2], forsale[3]])
            if birds_forsale['super'] >= forsale[1] and 'KANS' in forsale[0]:
                forsale_messages_list.append([user_id, 'bird', 'super', forsale[0], forsale[1], forsale[2], forsale[3]])
            if birds_forsale['founder'] >= forsale[1] and 'KANF' in forsale[0]:
                forsale_messages_list.append([user_id, 'bird', 'founder', forsale[0], forsale[1], forsale[2], forsale[3]])
            if birds_forsale['rare'] >= forsale[1] and 'KANR' in forsale[0]:
                forsale_messages_list.append([user_id, 'bird', 'rare', forsale[0], forsale[1], forsale[2], forsale[3]])
            if birds_forsale['limited'] >= forsale[1] and 'KANL' in forsale[0]:
                forsale_messages_list.append([user_id, 'bird', 'limited', forsale[0], forsale[1], forsale[2], forsale[3]])

    for forsale in forsale_list_items:
        forsale_rarity = fetch_metadata(db, forsale[0], forsale[3])['properties']['rarity']['value'].strip().lower()
        for user_id in items_forsale_by_user:
            items_forsale = items_forsale_by_user[user_id]
            if items_forsale['any'] >= forsale[1]:
                forsale_messages_list.append([user_id, 'item', 'any', forsale[0], forsale[1], forsale[2], forsale[3]])
            if items_forsale[forsale_rarity] >= forsale[1]:
                forsale_messages_list.append([user_id, 'item', forsale_rarity, forsale[0], forsale[1], forsale[2], forsale[3]])
    
    for forsale_message in forsale_messages_list:
        db.execute(f"INSERT INTO tg_forsale_messages(user_id, type, rarity, nft_id, price, block, metadata) VALUES ({forsale_message[0]},'{forsale_message[1]}','{forsale_message[2]}','{forsale_message[3]}',{forsale_message[4]:.3f},{forsale_message[5]},'{forsale_message[6]}');")
    conn.commit()

#Check dump updates
def check_update(bot, job):
    curr_time = round(time.time())
    conn = psycopg2.connect(dbname=pg_db, user=pg_login, 
                            password=pg_pass, host=pg_host)
    conn.set_client_encoding('UTF8')
    db = conn.cursor()
    db.execute("SELECT lastBlock FROM lastblock_vlite;")
    lastblock_v1 = db.fetchone()[0]
    db.execute("SELECT lastBlock FROM lastblock_v2;")
    lastblock_v2 = db.fetchone()[0]
    db.execute("SELECT * FROM tg_lastblocks;")
    tg_lastblock_v1, tg_lastblock_v2 = db.fetchone()

    #If last block updated
    if tg_lastblock_v1 != lastblock_v1 or tg_lastblock_v2 != lastblock_v2:
        update_changed_birds(conn, db, tg_lastblock_v1, tg_lastblock_v2)
        update_birds_gems_items(conn,db, tg_lastblock_v1, tg_lastblock_v2)
        update_records(conn, db, bot, tg_lastblock_v1, tg_lastblock_v2)
        update_nft_changes(conn, db, tg_lastblock_v1, tg_lastblock_v2)
        db.execute(f"UPDATE tg_lastblocks SET lastblock_v1={lastblock_v1}, lastblock_v2={lastblock_v2};")
        db.execute(f"INSERT INTO tg_block_history(block, approx_time) VALUES({max(lastblock_v1, lastblock_v2)}, {curr_time}) ON CONFLICT (block) DO NOTHING;")
        conn.commit()
    conn.close()