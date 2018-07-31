# RabbitMQ Delayed Delivery


This python script is meant to create the rabbitMq configuration for the [RabbitMQ delayed delivery pattern](https://docs.particular.net/transports/rabbitmq/delayed-delivery).

This pattern allow you to deliver message to rabbitmq queue and/or exchange after a certain time.

Here is a schema of the implementation :

![rabbitmq native delay infrastructure](https://static1.squarespace.com/static/56894e581c1210fead06f878/t/58ce946cebbd1a54a3444f12/1489933431912/NServiceBusDelayInfrastructure.png)


## Usage

``` shell
$ python --depth N [OPTION(S)]
```


### Arguments

 - `depth` : the size max of the int, in bits, used to determine the max duration of delayed delivery in seconds. Can be between 1 and 30. This argument in mandatory.
 - `vhost` : the vhost used for the configuration file.
 - `prefix` : a prefix used for the exchanges and queue, by default `ndd` (Native Delayed Delivery).
 - `dry-run` : print the configuration and exit.
 - `destination` : path of the destination file, if none given default file will be `rabbitmq-native-delayed-delivery-configuration.json`.
 - `only-time` : only print the max time and exit.
 - `remove-entry-point` : remove the entry point exchange.


## JSON output

Here is a json example of the output of the script :

``` json
{
	"exchanges": [
		{
			"vhost": "/",
			"durable": true,
			"auto_delete": false,
			"internal": false,
			"name": "ndd_exchange_dispatch",
			"type": "topic",
			"arguments": {}
		},
		{
			"vhost": "/",
			"durable": true,
			"auto_delete": false,
			"internal": false,
			"name": "ndd_exchange_delay-00",
			"type": "topic",
			"arguments": {}
		},
		{
			"vhost": "/",
			"durable": true,
			"auto_delete": false,
			"internal": false,
			"name": "ndd_exchange_delay-NN",
			"type": "topic",
			"arguments": {}
		},
		{
			"vhost": "/",
			"durable": true,
			"auto_delete": false,
			"internal": false,
			"name": "ndd_delivery_entry_point",
			"type": "topic",
			"arguments": {}
		}
	],
	"queues": [
		{
			"vhost": "/",
			"durable": true,
			"auto_delete": false,
			"name": "ndd_queue_delay-00",
			"arguments": {
				"x-dead-letter-exchange": "ndd_exchange_dispatch",
				"x-message-ttl": 1
			}
		},
		{
			"vhost": "/",
			"durable": true,
			"auto_delete": false,
			"name": "ndd_queue_delay-NN",
			"arguments": {
				"x-dead-letter-exchange": "ndd_exchange_delay-(N - 1)",
				"x-message-ttl": 2^N
			}
		}
	],
	"bindings": [
		{
			"vhost": "/",
			"destination_type": "exchange",
			"arguments": {},
			"source": "ndd_exchange_delay-00",
			"destination": "ndd_exchange_dispatch",
			"routing_key": "(N times *).0.*"
		},
		{
			"vhost": "/",
			"destination_type": "queue",
			"arguments": {},
			"source": "ndd_exchange_delay-00",
			"destination": "ndd_queue_delay-00",
			"routing_key": "(N times *).1.*"
		},
		{
			"vhost": "/",
			"destination_type": "exchange",
			"arguments": {},
			"source": "ndd_exchange_delay-NN",
			"destination": "ndd_exchange_delay-00",
			"routing_key": "(N - 1 times *).0.*.*"
		},
		{
			"vhost": "/",
			"destination_type": "queue",
			"arguments": {},
			"source": "ndd_exchange_delay-NN",
			"destination": "ndd_queue_delay-NN",
			"routing_key": "(N - 1 times *).1.*.*"
		},
		{
			"vhost": "/",
			"destination_type": "exchange",
			"arguments": {},
			"source": "ndd_delivery_entry_point",
			"destination": "ndd_exchange_delay-NN",
			"routing_key": "#"
		}
	]
}
```

`N` symbolize the depth set while generating the configuration file.



## Bind your retry exchanges

Don't forget to add to your configuration file the bindings between `ndd_exchange_dispatch`
and your retry exchanges (`ANY_RETRY_EXCHANGE_YOU_WANT_TO_BIND` in the exemple)

``` json
	{
		"vhost": "/",
		"destination_type": "exchange",
		"arguments": {},
		"source": "ndd_exchange_dispatch",
		"destination": "ANY_RETRY_EXCHANGE_YOU_WANT_TO_BIND",
		"routing_key": "#.ANY_RETRY_EXCHANGE_YOU_WANT_TO_BIND"
	},
```
