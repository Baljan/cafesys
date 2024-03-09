from django.dispatch import Signal


# Outbound message, before sending
# provides args: message, esp_name
pre_send = Signal()

# Outbound message, after sending
# provides args: message, status, esp_name
post_send = Signal()

# Delivery and tracking events for sent messages
# provides args: event, esp_name
tracking = Signal()

# Event for receiving inbound messages
# provides args: event, esp_name
inbound = Signal()


class AnymailEvent:
    """Base class for normalized Anymail webhook events"""

    def __init__(self, event_type, timestamp=None, event_id=None, esp_event=None, **kwargs):
        self.event_type = event_type  # normalized to an EventType str
        self.timestamp = timestamp  # normalized to an aware datetime
        self.event_id = event_id  # opaque str
        self.esp_event = esp_event  # raw event fields (e.g., parsed JSON dict or POST data QueryDict)


class AnymailTrackingEvent(AnymailEvent):
    """Normalized delivery and tracking event for sent messages"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.click_url = kwargs.pop('click_url', None)  # str
        self.description = kwargs.pop('description', None)  # str, usually human-readable, not normalized
        self.message_id = kwargs.pop('message_id', None)  # str, format may vary
        self.metadata = kwargs.pop('metadata', {})  # dict
        self.mta_response = kwargs.pop('mta_response', None)  # str, may include SMTP codes, not normalized
        self.recipient = kwargs.pop('recipient', None)  # str email address (just the email portion; no name)
        self.reject_reason = kwargs.pop('reject_reason', None)  # normalized to a RejectReason str
        self.tags = kwargs.pop('tags', [])  # list of str
        self.user_agent = kwargs.pop('user_agent', None)  # str


class AnymailInboundEvent(AnymailEvent):
    """Normalized inbound message event"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.message = kwargs.pop('message', None)  # anymail.inbound.AnymailInboundMessage


class EventType:
    """Constants for normalized Anymail event types"""

    # Delivery (and non-delivery) event types:
    # (these match message.ANYMAIL_STATUSES where appropriate)
    QUEUED = 'queued'  # the ESP has accepted the message and will try to send it (possibly later)
    SENT = 'sent'  # the ESP has sent the message (though it may or may not get delivered)
    REJECTED = 'rejected'  # the ESP refused to send the messsage (e.g., suppression list, policy, invalid email)
    FAILED = 'failed'  # the ESP was unable to send the message (e.g., template rendering error)

    BOUNCED = 'bounced'  # rejected or blocked by receiving MTA
    DEFERRED = 'deferred'  # delayed by receiving MTA; should be followed by a later BOUNCED or DELIVERED
    DELIVERED = 'delivered'  # accepted by receiving MTA
    AUTORESPONDED = 'autoresponded'  # a bot replied

    # Tracking event types:
    OPENED = 'opened'  # open tracking
    CLICKED = 'clicked'  # click tracking
    COMPLAINED = 'complained'  # recipient reported as spam (e.g., through feedback loop)
    UNSUBSCRIBED = 'unsubscribed'  # recipient attempted to unsubscribe
    SUBSCRIBED = 'subscribed'  # signed up for mailing list through ESP-hosted form

    # Inbound event types:
    INBOUND = 'inbound'  # received message
    INBOUND_FAILED = 'inbound_failed'

    # Other:
    UNKNOWN = 'unknown'  # anything else


class RejectReason:
    """Constants for normalized Anymail reject/drop reasons"""
    INVALID = 'invalid'  # bad address format
    BOUNCED = 'bounced'  # (previous) bounce from recipient
    TIMED_OUT = 'timed_out'  # (previous) repeated failed delivery attempts
    BLOCKED = 'blocked'  # ESP policy suppression
    SPAM = 'spam'  # (previous) spam complaint from recipient
    UNSUBSCRIBED = 'unsubscribed'  # (previous) unsubscribe request from recipient
    OTHER = 'other'
