"""
notifications.py -- pluggable, admin-configurable notification delivery.

Implements the NotificationChannel interface from
docs/notification-channels.md: one shared, pluggable interface for
delivering a non-secret prompt, admin-configurable per event type
(fan out to every enabled channel, not a fallback chain -- v1.0
delivery semantics, see the design doc).

Real call site (v1.0): ceremony invitations issued or backfilled in
app.py's initiate_ceremony() / _lapse_slot_locked(). The other two
event types the design doc names -- "envelope_ready" and
"drop_expired" -- have no real call site yet: they belong to
envelope-delivery.md's EnvelopeDropPoint, which isn't implemented
(today's /trustees/pending-envelope is synchronous polling with no
drop-point/TTL concept to notify about). The event_type string is
still free-form on NotificationEvent so wiring those in later is a
new call site, not an interface change.
"""

import smtplib
import ssl
from email.message import EmailMessage
from typing import Protocol

import requests


class NotificationEvent:
    def __init__(self, event_type: str, recipient_sub: str, recipient_username: str, metadata: dict):
        self.event_type = event_type              # "ceremony_invite" | "envelope_ready" | "drop_expired"
        self.recipient_sub = recipient_sub          # Keycloak `sub` of the trustee or operator
        self.recipient_username = recipient_username  # demo-only convenience for readable payloads
        self.metadata = metadata                    # event-specific, non-secret (ceremony_id, role, ttl, ...)


class NotificationChannel(Protocol):
    def send(self, event: NotificationEvent) -> None:
        """Deliver a prompt for `event`. Never carries a secret -- only
        enough for the recipient to know where to go act. Must not
        raise on its own transient delivery failures; log and return,
        so one channel's outage can't take down a caller fanning out
        to several enabled channels."""
        ...


class LogLineChannel:
    """Zero-configuration default -- prints to stdout, same as every
    other administrative event in this combiner. Always registered;
    what's admin-configurable is whether it's *enabled* for a given
    event type."""

    def send(self, event: NotificationEvent) -> None:
        print(f"[notify:{event.event_type}] {event.recipient_username}: {event.metadata}")


class WebhookChannel:
    """Generic operator-supplied webhook -- the deployer's own escape
    hatch, per notification-channel-concept.md's "generic outbound
    webhook" option. POSTs the event as JSON."""

    def __init__(self, url: str, timeout_s: float = 5.0):
        self._url = url
        self._timeout_s = timeout_s

    def send(self, event: NotificationEvent) -> None:
        payload = {
            "event_type": event.event_type,
            "recipient_username": event.recipient_username,
            "metadata": event.metadata,
        }
        try:
            requests.post(self._url, json=payload, timeout=self._timeout_s)
        except requests.RequestException as e:
            print(f"[notify:webhook] delivery failed (non-fatal): {e}")


class EmailChannel:
    """Demo/test-only: routes every notification through one real
    mailbox, using Gmail's "+suffix" addressing
    (mailbox+suffix@gmail.com) to simulate distinct recipients without
    provisioning separate mailboxes per candidate. NOT a pattern for a
    real deployment -- a real channel would resolve an actual
    per-trustee contact address from wherever the deployment's
    identity model tracks one, which this project's identity model
    deliberately doesn't (notification-channel-concept.md's stated
    constraint: "the identity model tracks no contact address")."""

    def __init__(self, smtp_host: str, smtp_port: int, username: str, app_password: str, base_address: str):
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._username = username
        self._app_password = app_password
        self._base_address = base_address  # e.g. "mailertest711@gmail.com"

    def _recipient_address(self, event: NotificationEvent) -> str:
        local, _, domain = self._base_address.partition("@")
        return f"{local}+{event.recipient_username}@{domain}"

    def _subject_and_body(self, event: NotificationEvent) -> tuple[str, str]:
        if event.event_type == "ceremony_invite":
            role = event.metadata.get("role")
            ceremony_id = event.metadata.get("ceremony_id")
            subject = f"shardic-envelope: you're invited ({role} trustee)"
            body = (
                f"You've been invited to participate in a shardic ceremony "
                f"as {role} trustee (ceremony {ceremony_id}).\n\n"
                f"No secret is included in this message -- open your "
                f"trustee app to respond."
            )
            return subject, body
        subject = f"shardic-envelope: {event.event_type.replace('_', ' ')}"
        body = f"{event.event_type}: {event.metadata}"
        return subject, body

    def send(self, event: NotificationEvent) -> None:
        to_addr = self._recipient_address(event)
        subject, body = self._subject_and_body(event)
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self._base_address
        msg["To"] = to_addr
        msg.set_content(body)
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(self._smtp_host, self._smtp_port, timeout=10) as server:
                server.starttls(context=context)
                server.login(self._username, self._app_password)
                server.send_message(msg)
        except (smtplib.SMTPException, OSError) as e:
            print(f"[notify:email] delivery failed (non-fatal): {e}")


class NotificationDispatcher:
    """Deployment-time config: which registered channels fire for
    which event type. v1.0 admin configuration surface: env-var at
    combiner startup, not a live-editable admin route -- see
    docs/notification-channels.md's "Admin configuration surface" open
    question."""

    def __init__(self, channels: dict[str, NotificationChannel], event_channels: dict[str, list[str]]):
        self._channels = channels
        self._event_channels = event_channels

    def notify(self, event: NotificationEvent) -> None:
        # v1.0 delivery semantics: fan out to every enabled channel for
        # this event type, not a fallback chain.
        for name in self._event_channels.get(event.event_type, []):
            channel = self._channels.get(name)
            if channel is not None:
                channel.send(event)


if __name__ == "__main__":
    events_sent = []

    class _RecordingChannel:
        def send(self, event: NotificationEvent) -> None:
            events_sent.append(event)

    dispatcher = NotificationDispatcher(
        channels={"a": _RecordingChannel(), "b": _RecordingChannel()},
        event_channels={"ceremony_invite": ["a", "b"], "drop_expired": ["a"]},
    )

    dispatcher.notify(NotificationEvent("ceremony_invite", "sub-1", "alice", {"role": "prime"}))
    assert len(events_sent) == 2, "fan-out should reach every enabled channel for the event type"
    print("fan-out to multiple enabled channels: OK")

    events_sent.clear()
    dispatcher.notify(NotificationEvent("drop_expired", "sub-2", "bob", {}))
    assert len(events_sent) == 1
    print("per-event-type channel selection: OK")

    events_sent.clear()
    dispatcher.notify(NotificationEvent("envelope_ready", "sub-3", "carol", {}))
    assert len(events_sent) == 0, "an event type with no configured channels sends nowhere, doesn't raise"
    print("unconfigured event type is a silent no-op: OK")

    print("All notifications.py self-tests passed.")
