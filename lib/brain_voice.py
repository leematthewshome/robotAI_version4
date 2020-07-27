#!/usr/bin/python3
"""
===============================================================================================
Common functions Used By robotai_brian and robotai_client
Author: Lee Matthews 2020
===============================================================================================
"""
import logging
import pymysql
import json
import pika


# create connection to database
# ----------------------------------------------------------------------------------
def createConn():
    try:
        conn = pymysql.connect(
            db='robotAI',
            user='root',
            passwd='Password123',
            host='localhost')
    except:
        return None
    return conn


# ---------------------------------------------------------------------------------
# Fetch a list of statements from the chat bot table
#----------------------------------------------------------------------------------
def getChatPath(chatid='0-GREETA-0'):
    # make 2 part chat IDs match the way 'next' column in DB formatted 
    arr = chatid.split('-')
    if len(arr) == 2:
        chatid = '0-' + chatid
    print('Running function getChatPath with chatid: ' + chatid)

    # connect to database and check for valid subscription
    conn = createConn()
    if conn is None:
        print('Could not connect to database. Exiting function.')
        return {}
    else:
        cur = conn.cursor()
        print('Connection to DB established and ready with cursor.')

    # function to build the SQL stmnt
    def buildSQL(table, sCat, iItm):
        SQL = "SELECT text, funct, next FROM " + table + " WHERE Category = '" + sCat + "'" 
        if str(iItm) != '0':
            SQL += " AND Item = " + str(iItm)
        else:
            SQL += " ORDER BY RAND() LIMIT 1 ;"
        return SQL
        
    # recursively loop through database to get path
    def chatLoop(chatid):
        list = []
        d = None
        row = chatid.split("-")
        sCat = row[1]
        iItm = row[2]
        
        # create SQL query (add multiple languages later)
        SQL = buildSQL('robotAI.ChatText_en', sCat, iItm)
        try:
            cur.execute(SQL)
            list = cur.fetchall()
        except:
            conn.rollback()

        # insert result into the json data object
        if len(list) > 0:
            d = {'text': list[0][0],
               'funct': list[0][1],
               'next': list[0][2]}
        else:
            d = {'text': 'Something went wrong. I could not find the requested chat entry ', 'funct': '', 'next': ''}
        return d

    # run the chat loop to build up our chat list and then return result
    chatlst = []
    while '|' not in chatid and len(chatid) > 0:
        row = chatLoop(chatid)
        chatlst.append(row)
        try:
            chatid = row['next']
        except:
            chatid = ''

    conn.close()

    return chatlst
    
    

#---------------------------------------------------------------------------
# Function called by robotAI_brain for this set of logic
#---------------------------------------------------------------------------
def doLogic(ENVIRON, QCONN, content, reply_to, body):
    debugOn = True
    action = ""
    
    # setup logging using the python logging library
    #-----------------------------------------------------
    logging.basicConfig()
    logger = logging.getLogger("brain_voice")
    if debugOn:
        logger.level = logging.DEBUG
    else:
        logger.level = logging.INFO

    # If we received JSON then get the requested action
    #-----------------------------------------------------
    if content == 'application/json':
        logger.debug('JSON received by brain_voice. Decoding...')
        try:
            data = json.loads(body.decode("utf-8"))
            action = data["action"]
        except:
            logger.error('Could not load response as JSON or extract key of "type"')
    elif content == 'audio/wav':
        logger.info('This is a placeholder for our speech to text functionality')
        action = "stt"

    logger.debug('Action value is: ' + action)

    # Execute requested VOICE action to execute
    #-----------------------------------------------------
    if action == "getChat":
        # need to fetch the relevant chat text requested 
        chatid = data["chatItem"]
        logger.debug('Calling getChatPath function')
        result = getChatPath(chatid)
        # return data to requested client 
        result = {'action': 'chat', 'list': result}
        body = json.dumps(result)
        logger.debug("Sending chat text to : " + reply_to)
        channel1 = QCONN.channel()
        channel1.queue_declare(reply_to)
        properties = pika.BasicProperties(app_id='voice', content_type='application/json', reply_to='Central')
        channel1.basic_publish(exchange='', routing_key=reply_to, body=body, properties=properties)
    elif action == "stt":
        # need to convert the recording to text and obtain intent
        logger.info('We need to develop a function to convert speech to text')
    else:
        # catch all if we didnt expect the action or was blank
        logger.warning('The action value of ' + action + ' has no code to handle it.')


