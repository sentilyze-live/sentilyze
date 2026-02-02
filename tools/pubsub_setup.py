#!/usr/bin/env python3
"""
Pub/Sub Setup Utility for Sentilyze

This script creates Pub/Sub topics and subscriptions for the Sentilyze
messaging infrastructure.

Usage:
    python pubsub_setup.py --project <project-id> --environment <env>
    python pubsub_setup.py --project my-project --environment dev --dry-run
"""

import argparse
import json
import sys
import time
from typing import Dict, List, Optional

try:
    from google.cloud import pubsub_v1
    from google.cloud.exceptions import Conflict, NotFound
    from google.api_core import retry
except ImportError:
    print("Error: google-cloud-pubsub is required. Install with: pip install google-cloud-pubsub")
    sys.exit(1)


# Topic configurations for Sentilyze
TOPIC_CONFIGS = {
    "sentiment-analysis-requests": {
        "description": "Queue for sentiment analysis requests",
        "labels": {"type": "processing", "priority": "high"},
        "message_retention_duration": "86400s",  # 24 hours
    },
    "sentiment-analysis-results": {
        "description": "Results from completed sentiment analysis",
        "labels": {"type": "results", "priority": "medium"},
        "message_retention_duration": "86400s",
    },
    "batch-job-events": {
        "description": "Events for batch job processing",
        "labels": {"type": "batch", "priority": "medium"},
        "message_retention_duration": "604800s",  # 7 days
    },
    "data-export-requests": {
        "description": "Requests for data exports",
        "labels": {"type": "export", "priority": "low"},
        "message_retention_duration": "86400s",
    },
    "system-events": {
        "description": "System-wide events and notifications",
        "labels": {"type": "system", "priority": "high"},
        "message_retention_duration": "604800s",
    },
    "dead-letter": {
        "description": "Dead letter queue for failed messages",
        "labels": {"type": "dead-letter", "priority": "low"},
        "message_retention_duration": "2592000s",  # 30 days
    },
}

# Subscription configurations
# Format: {topic_name: [{subscription_name: config}, ...]}
SUBSCRIPTION_CONFIGS = {
    "sentiment-analysis-requests": [
        {
            "name": "sentiment-worker-sub",
            "description": "Subscription for sentiment analysis workers",
            "ack_deadline_seconds": 60,
            "message_retention_duration": "86400s",
            "expiration_policy": {},  # Never expire
            "retry_policy": {
                "minimum_backoff": "10s",
                "maximum_backoff": "600s",
            },
            "dead_letter_policy": {
                "dead_letter_topic": "dead-letter",
                "max_delivery_attempts": 5,
            },
        },
        {
            "name": "sentiment-monitoring-sub",
            "description": "Subscription for monitoring/analysis",
            "ack_deadline_seconds": 10,
            "message_retention_duration": "3600s",
        },
    ],
    "sentiment-analysis-results": [
        {
            "name": "results-storage-sub",
            "description": "Subscription for storing results",
            "ack_deadline_seconds": 30,
            "message_retention_duration": "86400s",
        },
        {
            "name": "results-notification-sub",
            "description": "Subscription for result notifications",
            "ack_deadline_seconds": 10,
            "message_retention_duration": "3600s",
        },
    ],
    "batch-job-events": [
        {
            "name": "batch-processor-sub",
            "description": "Subscription for batch job processor",
            "ack_deadline_seconds": 120,
            "message_retention_duration": "604800s",
            "flow_control_settings": {
                "max_outstanding_messages": 100,
                "max_outstanding_bytes": 104857600,  # 100MB
            },
        },
    ],
    "data-export-requests": [
        {
            "name": "export-processor-sub",
            "description": "Subscription for export processor",
            "ack_deadline_seconds": 300,
            "message_retention_duration": "86400s",
        },
    ],
    "system-events": [
        {
            "name": "system-logger-sub",
            "description": "Subscription for system event logging",
            "ack_deadline_seconds": 10,
            "message_retention_duration": "604800s",
        },
        {
            "name": "alerting-sub",
            "description": "Subscription for alerting system",
            "ack_deadline_seconds": 10,
            "message_retention_duration": "604800s",
        },
    ],
}


class PubSubSetup:
    """Pub/Sub setup and configuration manager."""
    
    def __init__(self, project_id: str, environment: str, dry_run: bool = False):
        self.project_id = project_id
        self.environment = environment
        self.dry_run = dry_run
        self.topic_prefix = f"sentilyze-{environment}"
        
        if not dry_run:
            self.publisher_client = pubsub_v1.PublisherClient()
            self.subscriber_client = pubsub_v1.SubscriberClient()
        else:
            self.publisher_client = None
            self.subscriber_client = None
            print(f"[DRY RUN] Would use project: {project_id}")
    
    def _get_topic_path(self, topic_name: str) -> str:
        """Get the full topic path."""
        full_name = f"{self.topic_prefix}-{topic_name}"
        if self.dry_run:
            return f"projects/{self.project_id}/topics/{full_name}"
        return self.publisher_client.topic_path(self.project_id, full_name)
    
    def _get_subscription_path(self, subscription_name: str) -> str:
        """Get the full subscription path."""
        full_name = f"{self.topic_prefix}-{subscription_name}"
        if self.dry_run:
            return f"projects/{self.project_id}/subscriptions/{full_name}"
        return self.subscriber_client.subscription_path(self.project_id, full_name)
    
    def create_topic(self, topic_name: str, config: Dict) -> bool:
        """Create a Pub/Sub topic."""
        topic_path = self._get_topic_path(topic_name)
        full_name = f"{self.topic_prefix}-{topic_name}"
        
        if self.dry_run:
            print(f"[DRY RUN] Would create topic: {full_name}")
            return True
        
        try:
            # Check if topic exists
            try:
                self.publisher_client.get_topic(request={"topic": topic_path})
                print(f"✓ Topic already exists: {full_name}")
                return True
            except NotFound:
                pass
            
            # Create topic
            topic = self.publisher_client.create_topic(
                request={
                    "name": topic_path,
                    "labels": {**config.get("labels", {}), "environment": self.environment},
                }
            )
            
            print(f"✓ Topic created: {full_name}")
            
            # Set message retention if specified
            if "message_retention_duration" in config:
                # Note: Message retention is set at topic creation or via update
                pass
            
            return True
            
        except Conflict:
            print(f"✓ Topic already exists: {full_name}")
            return True
        except Exception as e:
            print(f"✗ Error creating topic {full_name}: {e}")
            return False
    
    def create_subscription(
        self, 
        topic_name: str, 
        subscription_config: Dict
    ) -> bool:
        """Create a Pub/Sub subscription."""
        topic_path = self._get_topic_path(topic_name)
        subscription_name = subscription_config["name"]
        subscription_path = self._get_subscription_path(subscription_name)
        full_name = f"{self.topic_prefix}-{subscription_name}"
        
        if self.dry_run:
            print(f"  [DRY RUN] Would create subscription: {full_name}")
            return True
        
        try:
            # Check if subscription exists
            try:
                self.subscriber_client.get_subscription(
                    request={"subscription": subscription_path}
                )
                print(f"  ✓ Subscription already exists: {full_name}")
                return True
            except NotFound:
                pass
            
            # Build subscription configuration
            subscription = {
                "name": subscription_path,
                "topic": topic_path,
                "ack_deadline_seconds": subscription_config.get("ack_deadline_seconds", 10),
            }
            
            # Add optional configurations
            if "message_retention_duration" in subscription_config:
                subscription["message_retention_duration"] = subscription_config[
                    "message_retention_duration"
                ]
            
            if "expiration_policy" in subscription_config:
                subscription["expiration_policy"] = subscription_config["expiration_policy"]
            
            if "retry_policy" in subscription_config:
                subscription["retry_policy"] = subscription_config["retry_policy"]
            
            if "dead_letter_policy" in subscription_config:
                # Get dead letter topic path
                dead_letter_topic = subscription_config["dead_letter_policy"]["dead_letter_topic"]
                dead_letter_path = self._get_topic_path(dead_letter_topic)
                
                subscription["dead_letter_policy"] = {
                    "dead_letter_topic": dead_letter_path,
                    "max_delivery_attempts": subscription_config["dead_letter_policy"][
                        "max_delivery_attempts"
                    ],
                }
            
            # Create subscription
            self.subscriber_client.create_subscription(request=subscription)
            print(f"  ✓ Subscription created: {full_name}")
            
            return True
            
        except Conflict:
            print(f"  ✓ Subscription already exists: {full_name}")
            return True
        except Exception as e:
            print(f"  ✗ Error creating subscription {full_name}: {e}")
            return False
    
    def setup_topics(self) -> bool:
        """Create all configured topics."""
        print(f"\nSetting up topics for environment: {self.environment}")
        print("=" * 60)
        
        all_success = True
        for topic_name, config in TOPIC_CONFIGS.items():
            if not self.create_topic(topic_name, config):
                all_success = False
        
        return all_success
    
    def setup_subscriptions(self) -> bool:
        """Create all configured subscriptions."""
        print(f"\nSetting up subscriptions for environment: {self.environment}")
        print("=" * 60)
        
        all_success = True
        for topic_name, subscriptions in SUBSCRIPTION_CONFIGS.items():
            print(f"\nTopic: {self.topic_prefix}-{topic_name}")
            
            for sub_config in subscriptions:
                if not self.create_subscription(topic_name, sub_config):
                    all_success = False
        
        return all_success
    
    def test_messaging(self) -> bool:
        """Test Pub/Sub messaging by publishing and receiving a test message."""
        print(f"\nTesting Pub/Sub messaging")
        print("=" * 60)
        
        if self.dry_run:
            print("[DRY RUN] Skipping message test")
            return True
        
        # Use system-events topic for testing
        topic_name = "system-events"
        topic_path = self._get_topic_path(topic_name)
        
        test_subscription_name = f"test-{int(time.time())}"
        test_subscription_path = self._get_subscription_path(test_subscription_name)
        
        try:
            # Create temporary subscription
            print(f"Creating test subscription: {test_subscription_name}")
            self.subscriber_client.create_subscription(
                request={
                    "name": test_subscription_path,
                    "topic": topic_path,
                    "ack_deadline_seconds": 10,
                }
            )
            
            # Publish test message
            test_message = {
                "type": "test",
                "timestamp": time.time(),
                "message": "Pub/Sub test message",
            }
            
            print("Publishing test message...")
            future = self.publisher_client.publish(
                topic_path,
                json.dumps(test_message).encode("utf-8"),
                test="true",
            )
            message_id = future.result()
            print(f"✓ Published message: {message_id}")
            
            # Receive message
            print("Receiving test message...")
            response = self.subscriber_client.pull(
                request={"subscription": test_subscription_path, "max_messages": 1},
                timeout=30,
            )
            
            if response.received_messages:
                received_message = response.received_messages[0]
                data = json.loads(received_message.message.data.decode("utf-8"))
                
                if data["type"] == "test":
                    print("✓ Successfully received test message")
                    
                    # Acknowledge message
                    self.subscriber_client.acknowledge(
                        request={
                            "subscription": test_subscription_path,
                            "ack_ids": [received_message.ack_id],
                        }
                    )
                else:
                    print("✗ Received unexpected message")
                    return False
            else:
                print("✗ No message received within timeout")
                return False
            
            return True
            
        except Exception as e:
            print(f"✗ Error during messaging test: {e}")
            return False
        finally:
            # Clean up test subscription
            try:
                self.subscriber_client.delete_subscription(
                    request={"subscription": test_subscription_path}
                )
                print(f"✓ Cleaned up test subscription")
            except Exception as e:
                print(f"Warning: Could not clean up test subscription: {e}")
    
    def list_topics(self) -> List[str]:
        """List all topics in the project with the environment prefix."""
        if self.dry_run:
            return []
        
        project_path = f"projects/{self.project_id}"
        topics = []
        
        for topic in self.publisher_client.list_topics(request={"project": project_path}):
            if f"{self.topic_prefix}-" in topic.name:
                topics.append(topic.name)
        
        return topics
    
    def list_subscriptions(self) -> List[str]:
        """List all subscriptions in the project with the environment prefix."""
        if self.dry_run:
            return []
        
        project_path = f"projects/{self.project_id}"
        subscriptions = []
        
        for subscription in self.subscriber_client.list_subscriptions(
            request={"project": project_path}
        ):
            if f"{self.topic_prefix}-" in subscription.name:
                subscriptions.append(subscription.name)
        
        return subscriptions
    
    def export_config(self, output_file: Optional[str] = None) -> None:
        """Export topic and subscription configurations to a JSON file."""
        config = {
            "project_id": self.project_id,
            "environment": self.environment,
            "topics": {},
            "subscriptions": {},
        }
        
        for topic_name, topic_config in TOPIC_CONFIGS.items():
            full_name = f"{self.topic_prefix}-{topic_name}"
            config["topics"][full_name] = topic_config
        
        for topic_name, subs in SUBSCRIPTION_CONFIGS.items():
            full_topic_name = f"{self.topic_prefix}-{topic_name}"
            config["subscriptions"][full_topic_name] = []
            for sub in subs:
                full_sub_name = f"{self.topic_prefix}-{sub['name']}"
                config["subscriptions"][full_topic_name].append({
                    "name": full_sub_name,
                    **sub
                })
        
        if output_file is None:
            output_file = f"pubsub_config_{self.environment}.json"
        
        with open(output_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✓ Configuration exported to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Pub/Sub Setup Utility for Sentilyze",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pubsub_setup.py --project my-project --environment dev
  python pubsub_setup.py --project my-project --environment prod --dry-run
  python pubsub_setup.py --project my-project --environment dev --test-only
        """
    )
    
    parser.add_argument(
        "--project",
        required=True,
        help="GCP project ID"
    )
    parser.add_argument(
        "--environment",
        required=True,
        choices=["dev", "staging", "prod"],
        help="Environment (dev/staging/prod)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without executing"
    )
    parser.add_argument(
        "--test-only",
        action="store_true",
        help="Only run messaging tests"
    )
    parser.add_argument(
        "--export-config",
        action="store_true",
        help="Export configuration to JSON and exit"
    )
    parser.add_argument(
        "--skip-test",
        action="store_true",
        help="Skip messaging test"
    )
    
    args = parser.parse_args()
    
    # Initialize setup
    setup = PubSubSetup(
        project_id=args.project,
        environment=args.environment,
        dry_run=args.dry_run
    )
    
    # Export config and exit if requested
    if args.export_config:
        setup.export_config()
        return 0
    
    # Test only mode
    if args.test_only:
        if setup.test_messaging():
            print("\n✓ Messaging test passed")
            return 0
        else:
            print("\n✗ Messaging test failed")
            return 1
    
    # Full setup
    print("=" * 60)
    print("Sentilyze Pub/Sub Setup")
    print(f"Project: {args.project}")
    print(f"Environment: {args.environment}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print("=" * 60)
    
    success = True
    
    # Create topics
    if not setup.setup_topics():
        success = False
    
    # Create subscriptions
    if not setup.setup_subscriptions():
        success = False
    
    # Test messaging
    if not args.skip_test and not args.dry_run:
        if not setup.test_messaging():
            success = False
    
    # Final status
    print("\n" + "=" * 60)
    if success:
        print("✓ Pub/Sub setup completed successfully!")
        print("=" * 60)
        
        # List created resources
        if not args.dry_run:
            topics = setup.list_topics()
            subscriptions = setup.list_subscriptions()
            print(f"\nCreated {len(topics)} topics and {len(subscriptions)} subscriptions")
        
        return 0
    else:
        print("✗ Pub/Sub setup completed with errors")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
