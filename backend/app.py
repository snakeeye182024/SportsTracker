import json
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import TypeSerializer

TABLE = None

def table():
    global TABLE
    if TABLE is None:
        TABLE = boto3.resource('dynamodb').Table(os.environ['TABLE_NAME'])
    return TABLE


def reply(status, data):
    return {'statusCode': status, 'headers': {'content-type': 'application/json', 'cache-control': 'no-store'}, 'body': json.dumps(data, default=lambda v: float(v) if isinstance(v, Decimal) else str(v))}


def fail(status, message):
    return reply(status, {'error': message})


def load_body(event):
    raw = event.get('body') or '{}'
    if event.get('isBase64Encoded'):
        raise ValueError('Base64 request bodies are not supported')
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise ValueError('Body must be a JSON object')
    return obj


def name_field(body, field, maximum=120):
    val = body.get(field)
    if not isinstance(val, str) or not val.strip() or len(val.strip()) > maximum:
        raise ValueError(f'{field} must be 1–{maximum} characters')
    return val.strip()


def now():
    return datetime.now(timezone.utc).isoformat()


def owner_key(sub):
    return f'USER#{sub}'


def league_key(league_id):
    return f'LEAGUE#{league_id}'


def league_for_user(league_id, sub):
    item = table().get_item(Key={'PK': league_key(league_id), 'SK': 'META'}, ConsistentRead=True).get('Item')
    if not item or item.get('ownerSub') != sub:
        return None
    return item


def query(pk, prefix):
    result = table().query(KeyConditionExpression=Key('PK').eq(pk) & Key('SK').begins_with(prefix))
    return result.get('Items', [])


def handler(event, context):
    method = event.get('requestContext', {}).get('http', {}).get('method', '')
    path = event.get('rawPath', '')
    if path == '/v1/health' and method == 'GET':
        return reply(200, {'status': 'ok', 'version': '2.0'})
    claims = event.get('requestContext', {}).get('authorizer', {}).get('jwt', {}).get('claims', {})
    sub = claims.get('sub')
    if not sub:
        return fail(401, 'Authentication required')
    parts = [p for p in path.split('/') if p]
    if not parts or parts[0] != 'v1':
        return fail(404, 'Not found')
    try:
        if parts == ['v1', 'leagues']:
            if method == 'GET':
                memberships = query(owner_key(sub), 'LEAGUE#')
                leagues = []
                for m in memberships:
                    obj = league_for_user(m['leagueId'], sub)
                    if obj:
                        leagues.append(obj)
                return reply(200, {'items': leagues})
            if method == 'POST':
                body = load_body(event)
                title = name_field(body, 'name')
                season = name_field(body, 'season', 40)
                sport = body.get('sport', 'baseball')
                if sport not in ('baseball', 'softball'):
                    raise ValueError('sport must be baseball or softball')
                lid = str(uuid.uuid4())
                item = {'PK': league_key(lid), 'SK': 'META', 'leagueId': lid, 'name': title, 'season': season, 'sport': sport, 'ownerSub': sub, 'createdAt': now()}
                serializer = TypeSerializer()
                membership = {'PK': owner_key(sub), 'SK': f'LEAGUE#{lid}', 'leagueId': lid}
                def encode(record):
                    return {k: serializer.serialize(v) for k, v in record.items()}
                boto3.client('dynamodb').transact_write_items(TransactItems=[
                    {'Put': {'TableName': os.environ['TABLE_NAME'], 'Item': encode(item), 'ConditionExpression': 'attribute_not_exists(PK)'}},
                    {'Put': {'TableName': os.environ['TABLE_NAME'], 'Item': encode(membership), 'ConditionExpression': 'attribute_not_exists(PK)'}}
                ])
                return reply(201, item)
        if len(parts) >= 3 and parts[1] == 'leagues':
            lid = parts[2]
            league = league_for_user(lid, sub)
            if not league:
                return fail(404, 'League not found')
            if len(parts) == 3 and method == 'GET':
                return reply(200, league)
            if len(parts) == 4 and parts[3] == 'teams':
                if method == 'GET':
                    return reply(200, {'items': query(league_key(lid), 'TEAM#')})
                if method == 'POST':
                    body = load_body(event)
                    name = name_field(body, 'name')
                    tid = str(uuid.uuid4())
                    item = {'PK': league_key(lid), 'SK': f'TEAM#{tid}', 'leagueId': lid, 'teamId': tid, 'name': name, 'createdAt': now()}
                    table().put_item(Item=item, ConditionExpression='attribute_not_exists(PK)')
                    return reply(201, item)
            if len(parts) == 6 and parts[3] == 'teams' and parts[5] == 'players':
                tid = parts[4]
                team = table().get_item(Key={'PK': league_key(lid), 'SK': f'TEAM#{tid}'}).get('Item')
                if not team:
                    return fail(404, 'Team not found')
                if method == 'GET':
                    return reply(200, {'items': query(f'TEAM#{tid}', 'PLAYER#')})
                if method == 'POST':
                    body = load_body(event)
                    player_name = name_field(body, 'name')
                    number = str(body.get('number', '')).strip()
                    position = str(body.get('position', '')).strip()
                    if len(number) > 5 or len(position) > 30:
                        raise ValueError('Invalid number or position')
                    pid = str(uuid.uuid4())
                    item = {'PK': f'TEAM#{tid}', 'SK': f'PLAYER#{pid}', 'playerId': pid, 'teamId': tid, 'name': player_name, 'number': number, 'position': position, 'createdAt': now()}
                    table().put_item(Item=item, ConditionExpression='attribute_not_exists(PK)')
                    return reply(201, item)
        return fail(404, 'Route not found')
    except (ValueError, json.JSONDecodeError) as e:
        return fail(400, str(e))
    except Exception:
        print('Unexpected server error', flush=True)
        raise
