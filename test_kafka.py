from kafka_integration import SoccerAnalystKafkaManager, TOPICS
import time
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_kafka_connection():
    try:
        # Initialize Kafka manager
        kafka_manager = SoccerAnalystKafkaManager()
        logger.info("Successfully initialized Kafka manager")

        # Test producer
        test_data = {
            "test": "message",
            "timestamp": time.time()
        }
        
        # Publish test message
        kafka_manager.publish_match_data("test_match_1", test_data)
        logger.info("Successfully published test message")

        # Test consumer
        consumer = kafka_manager.get_consumer([TOPICS['matches']])
        logger.info("Successfully created consumer")

        # Try to consume message
        message = consumer.consume_messages(timeout=5.0)
        if message:
            logger.info(f"Successfully consumed message: {message}")
        else:
            logger.warning("No message received within timeout")

        # Cleanup
        consumer.close()
        kafka_manager.close_all_consumers()
        logger.info("Successfully closed all connections")

        return True

    except Exception as e:
        logger.error(f"Kafka test failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_kafka_connection()
    if success:
        print("Kafka connection test passed!")
    else:
        print("Kafka connection test failed!") 