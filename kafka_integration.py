from confluent_kafka import Producer, Consumer, KafkaError
from typing import Dict, Any, Optional, List
import json
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Kafka configuration
KAFKA_CONFIG = {
    'bootstrap.servers': '127.0.0.1:9092',
    'client.id': 'soccer_analyst_client',
    'group.id': 'soccer_analyst_group',
    'socket.timeout.ms': 6000,
    'reconnect.backoff.ms': 1000,
    'reconnect.backoff.max.ms': 10000,
    'retry.backoff.ms': 1000
}

# Kafka topics
TOPICS = {
    'matches': 'soccer_matches',
    'standings': 'soccer_standings',
    'team_stats': 'soccer_team_stats',
    'match_analysis': 'soccer_match_analysis'
}

class KafkaProducer:
    def __init__(self):
        try:
            self.producer = Producer(KAFKA_CONFIG)
            logger.info("Successfully initialized Kafka producer")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {str(e)}")
            raise
        
    def delivery_report(self, err, msg):
        if err is not None:
            logger.error(f'Message delivery failed: {err}')
        else:
            logger.info(f'Message delivered to {msg.topic()} [{msg.partition()}]')

    def produce_message(self, topic: str, key: str, value: Dict[str, Any]):
        """Produce a message to a Kafka topic"""
        try:
            # Add timestamp to the message
            value['timestamp'] = datetime.now().isoformat()
            
            # Produce message
            self.producer.produce(
                topic=topic,
                key=key.encode('utf-8'),
                value=json.dumps(value).encode('utf-8'),
                callback=self.delivery_report
            )
            # Flush to ensure message is sent
            self.producer.flush()
            
        except Exception as e:
            logger.error(f'Error producing message: {str(e)}')
            raise

class KafkaConsumer:
    def __init__(self, topics: List[str]):
        try:
            self.consumer = Consumer({
                **KAFKA_CONFIG,
                'auto.offset.reset': 'earliest'
            })
            self.topics = topics
            self.consumer.subscribe(topics)
            logger.info(f"Successfully initialized Kafka consumer for topics: {topics}")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka consumer: {str(e)}")
            raise
        
    def consume_messages(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """Consume messages from subscribed topics"""
        try:
            msg = self.consumer.poll(timeout)
            
            if msg is None:
                return None
                
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    logger.info('Reached end of partition')
                else:
                    logger.error(f'Error while consuming message: {msg.error()}')
                return None
                
            # Decode and parse message
            value = json.loads(msg.value().decode('utf-8'))
            key = msg.key().decode('utf-8') if msg.key() else None
            
            return {
                'topic': msg.topic(),
                'partition': msg.partition(),
                'offset': msg.offset(),
                'key': key,
                'value': value
            }
            
        except Exception as e:
            logger.error(f'Error consuming message: {str(e)}')
            return None
            
    def close(self):
        """Close the consumer connection"""
        self.consumer.close()

class SoccerAnalystKafkaManager:
    def __init__(self):
        self.producer = KafkaProducer()
        self.consumers = {}
        
    def publish_match_data(self, match_id: str, match_data: Dict[str, Any]):
        """Publish match data to Kafka"""
        self.producer.produce_message(
            topic=TOPICS['matches'],
            key=match_id,
            value=match_data
        )
        
    def publish_standings_update(self, standings_data: Dict[str, Any]):
        """Publish standings update to Kafka"""
        self.producer.produce_message(
            topic=TOPICS['standings'],
            key=datetime.now().strftime('%Y%m%d'),
            value=standings_data
        )
        
    def publish_team_stats(self, team_id: str, team_stats: Dict[str, Any]):
        """Publish team statistics to Kafka"""
        self.producer.produce_message(
            topic=TOPICS['team_stats'],
            key=team_id,
            value=team_stats
        )
        
    def publish_match_analysis(self, match_id: str, analysis: Dict[str, Any]):
        """Publish match analysis to Kafka"""
        self.producer.produce_message(
            topic=TOPICS['match_analysis'],
            key=match_id,
            value=analysis
        )
        
    def get_consumer(self, topics: List[str]) -> KafkaConsumer:
        """Get or create a consumer for specified topics"""
        topics_key = ','.join(sorted(topics))
        if topics_key not in self.consumers:
            self.consumers[topics_key] = KafkaConsumer(topics)
        return self.consumers[topics_key]
        
    def close_all_consumers(self):
        """Close all consumer connections"""
        for consumer in self.consumers.values():
            consumer.close()
        self.consumers.clear()

# Example usage in real-time data processing
class RealTimeDataProcessor:
    def __init__(self):
        self.kafka_manager = SoccerAnalystKafkaManager()
        
    def process_match_updates(self):
        """Process real-time match updates"""
        consumer = self.kafka_manager.get_consumer([TOPICS['matches']])
        
        while True:
            message = consumer.consume_messages()
            if message:
                # Process match update
                match_data = message['value']
                # Update ChromaDB or trigger other processing
                logger.info(f"Processing match update: {match_data['match_id']}")
                
    def process_standings_updates(self):
        """Process standings updates"""
        consumer = self.kafka_manager.get_consumer([TOPICS['standings']])
        
        while True:
            message = consumer.consume_messages()
            if message:
                # Process standings update
                standings_data = message['value']
                # Update ChromaDB or trigger visualization updates
                logger.info("Processing standings update") 