import inspect

try:
    import json
except ImportError:
    import simplejson as json
import yaml

from scalarizr.adm.command import Command
from scalarizr.adm.command import RuntimeError
from scalarizr.util import system2
from scalarizr.adm.util import make_table
from scalarizr.adm.util import encode
from scalarizr.messaging import Message
from scalarizr.bus import bus


def _szr_string_representer(dumper, data):
    data_encodings = (('ascii', u'tag:yaml.org,2002:str', unicode),
                      ('utf-8', u'tag:yaml.org,2002:python/str', unicode),
                      ('base64', u'tag:yaml.org,2002:binary', lambda x, y: x.encode(y)))

    for i, (encoding, tag, method) in enumerate(data_encodings):
        try:
            encoded_data = method(data, encoding)
            style = '|' if ('\n' in data or len(data) >= 128) else None
            return dumper.represent_scalar(tag, encoded_data, style)
        except ValueError:
            if i == len(data_encodings) - 1:
                raise


yaml.add_representer(str, _szr_string_representer)


db_connection = bus.db


class ListMessages(Command):
    """
    Display list of messages that were sent/recieved on this server.

    Usage:
      list-messages [--name=<name>]

    Options:
      -n, --name=<name>  Message id
    """
    aliases = ['lm']

    def display(self, data):
        for row in data:
            row[3] = 'in' if row[3] else 'out'
            row[4] = 'yes' if row[4] else 'no'

        header_fields = ['id', 'name', 'date', 'direction', 'handled?']
        table = make_table(res, header_fields)
        print table

    def __call__(self, name=None):
        try:
            cursor = db_connection.cursor()
            query = "SELECT `message_id`,`message_name`,\
                `out_last_attempt_time`,`is_ingoing`,`in_is_handled`\
                FROM p2p_message"
            if name:
                query += " WHERE `message_name`='%s'" % name

            cursor.execute(query)
            data = cursor.fetchall()
            self.display(data)

        finally:
            cursor.close()


class MessageDetails(Command):
    """
    Displays details of message with given id.

    Usage:
      message-details [--json] <message_id>

    Options:
      -j, --json
    """

    def __call__(self, message_id, json=False):
        try:
            cursor = db_connection.cursor()

            query = "SELECT `message`,`format` FROM p2p_message " \
                "WHERE `message_id`='%s'" % message_id
            cursor.execute(query)
            fetched_data = cursor.fetchone()
        finally:
            cursor.close()

        if fetched_data:
            msg = Message()
            msg_format = fetched_data[1]
            if msg_format == 'json':
                msg.fromjson(fetched_data[0]) 
            else:
                msg.fromxml(fetched_data[0])

            mdict = encode({'id': msg.id,
                            'name': msg.name,
                            'meta': msg.meta,
                            'body': msg.body})

            if json:
                print json.dumps(mdict, indent=4, sort_keys=True)
            else:
                print yaml.dump(mdict, default_flow_style=False)
        else:
            raise RuntimeError('Message not found')


class MarkAsUnhandled(Command):
    """
    Marks message with given id as unhandled

    Usage:
      mark-as-unhandled <message_id>
    """

    def display(self, data):
        for row in data:
            row[3] = 'in' if row[3] else 'out'
            row[4] = 'yes' if row[4] else 'no'

        header_fields = ['id', 'name', 'date', 'direction', 'handled?']
        table = make_table(res, header_fields)
        print table
    
    def __call__(self, message_id):
        try:
            cursor = db_connection.cursor()

            query = "UPDATE p2p_message SET in_is_handled = 0 WHERE message_id = '%s'"
            cursor.execute(query % message_id)
            db_connection.commit()
            cursor.close()

            cursor = db_connection.cursor()
            query = "SELECT `message_id`,`message_name`,`out_last_attempt_time`," \
                "`is_ingoing`,`in_is_handled` FROM p2p_message WHERE `message_id`='%s'"
            cursor.execute(query % message_id)

            data = cursor.fetchall()
            self.display(data)
        finally:
            cursor.close()


commands = [ListMessages,
    MessageDetails,
    MarkAsUnhandled]
