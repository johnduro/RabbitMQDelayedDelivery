# encoding=utf8

import argparse
import json
from datetime import datetime, timedelta
from collections import OrderedDict

MAX_SIZE = 30
VHOST = '/'
PREFIX = 'ndd'
DESTINATION = 'rabbitmq-native-delayed-delivery-configuration.json'
EXIT_EXCHANGE = 'exchange_dispatch'
ENTRY_POINT = 'delivery_entry_point'

class _Config:
    def __init__(self, args):
        if args.depth is None or int(args.depth[0]) < 1 or int(args.depth[0]) > MAX_SIZE:
            raise Exception("argument --depth should be set, not inferior to 1 or superior to " + str(MAX_SIZE))
        self.depth = int(args.depth[0])
        self.vhost = args.vhost[0] if args.vhost is not None else VHOST
        self.prefix = args.prefix[0] if args.prefix is not None else PREFIX
        self.destination = args.destination[0] if args.destination is not None else DESTINATION
        self.dryRun = args.dry_run
        self.onlyTime = args.only_time
        self.addEntryPoint = not args.remove_entry_point



class _RabbitMqConfig:
    def __init__(self, dispatchExchange):
        self.exchanges = [dispatchExchange]
        self.queues = []
        self.bindings = []


    def addExchange(self, exchange):
        self.exchanges.append(exchange)


    def addQueue(self, queue):
        self.queues.append(queue)


    def addBinding(self, binding):
        self.bindings.append(binding)


    def lastExchange(self):
        return self.exchanges[-1]


    def toArray(self):
        return OrderedDict([
            ('exchanges', self.exchanges),
            ('queues', self.queues),
            ('bindings', self.bindings)
        ])



class _RabbitMqConfigGenerator:
    def __init__(self, config):
        self.config = config


    def getPrefix(self):
        if not self.config.prefix:
            return ''

        return self.config.prefix + '_'


    def getExchange(self, name, exchangeType='topic'):
        return OrderedDict([
            ('vhost', self.config.vhost),
            ('durable', True),
            ('auto_delete', False),
            ('internal', False),
            ('name', self.getPrefix() + name),
            ('type', exchangeType),
            ('arguments', {}),
        ])


    def getQueue(self, name, previousExchange, ttlInSeconds):
        return OrderedDict([
            ('vhost', self.config.vhost),
            ('durable', True),
            ('auto_delete', False),
            ('name', self.getPrefix() + name),
            ('arguments', {
                'x-dead-letter-exchange': previousExchange,
                'x-message-ttl': ttlInSeconds * 1000,
            })
        ])

    def getBinding(self, source, destination, destinationType, routing_key):
        return OrderedDict([
            ('vhost', self.config.vhost),
            ('arguments', {}),
            ('source', self.getPrefix() + source),
            ('destination', destination),
            ('destination_type', destinationType),
            ('routing_key', routing_key)
        ])


    def getRoutingKey(self, bit, value):
        bits = ['#'] + ['*' for x in range(self.config.depth + 1)]
        bits[bit + 1] = value
        bits.reverse()

        return '.'.join(bits)


    def addBitToConfiguration(self, configuration, bit):
        lastExchangeName = configuration.lastExchange()['name']
        baseName = 'delay-' + ("%02d" % bit)
        exchangeName = 'exchange_' + baseName
        queueName = 'queue_' + baseName

        configuration.addExchange(
            self.getExchange(exchangeName)
        )
        configuration.addQueue(
            self.getQueue(queueName, lastExchangeName, 2 ** bit)
        )
        configuration.addBinding(
            self.getBinding(exchangeName, lastExchangeName, 'exchange', self.getRoutingKey(bit, '0'))
        )
        configuration.addBinding(
            self.getBinding(exchangeName, self.getPrefix() + queueName, 'queue', self.getRoutingKey(bit, '1'))
        )


    def addEntryPoint(self, configuration):
        lastExchangeName = configuration.lastExchange()['name']
        configuration.addExchange(
            self.getExchange(ENTRY_POINT)
        )
        configuration.addBinding(
            self.getBinding(ENTRY_POINT, lastExchangeName, 'exchange', '#')
        )



    def generate(self):
        configuration = _RabbitMqConfig(self.getExchange(EXIT_EXCHANGE))

        for bit in range(self.config.depth + 1):
            self.addBitToConfiguration(configuration, bit)

        if self.config.addEntryPoint:
            self.addEntryPoint(configuration)

        return configuration



def printMaxTime(depth):
    maxTimeInSeconds = (2 ** (depth + 1)) - 1
    maxTimeInMinutes = maxTimeInSeconds / 60
    maxTimeInHours = maxTimeInMinutes / 60
    maxTimeInDays = maxTimeInHours / 24
    maxTimeInYears = maxTimeInDays / 365
    print("The max time you choosed is:")
    print("   - in seconds: " + str(maxTimeInSeconds))
    print("   - in minutes: " + str(maxTimeInMinutes))
    print("   - in hours: " + str(maxTimeInHours))
    print("   - in days: " + str(maxTimeInDays))
    print("   - in years " + str(maxTimeInYears))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--depth', help='the depth of the delayed delivery', nargs=1)
    parser.add_argument('-v', '--vhost', help='the vhost to use', nargs=1)
    parser.add_argument('-p', '--prefix', help='the prefix of the queue and exchange', nargs=1)
    parser.add_argument('--dry-run', help='print the configuration and exit', action='store_true')
    parser.add_argument('--destination', help='path of the destination file', nargs=1)
    parser.add_argument('--only-time', help='print only the time and exit', action='store_true')
    parser.add_argument('--remove-entry-point', help='remove the entry point exchange', action='store_true')
    args = parser.parse_args()

    try:
        config = _Config(args)
        printMaxTime(config.depth)
        if config.onlyTime:
            exit()
        generator = _RabbitMqConfigGenerator(config)
        configuration = generator.generate()

        if config.dryRun:
            print('CONFIGURATION : ')
            print(json.dumps(configuration.toArray(), indent=4))
        else:
            with open(config.destination, 'w') as outFile:
                json.dump(configuration.toArray(), outFile, indent=4)
                print('Configuration was generated in file : ' + config.destination)
                if config.addEntryPoint:
                    print('Entry point exchange : ' + generator.getPrefix() + ENTRY_POINT)
                print('Exit point exchange : ' + generator.getPrefix() + EXIT_EXCHANGE)
    except Exception as exp:
        print("An error occured:")
        print("     " + exp.args[0])

main()
