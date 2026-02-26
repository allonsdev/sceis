import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker
from app.models import *

fake = Faker()


class Command(BaseCommand):
    help = "Seeds all CRM, analytics, and task models with demo data"

    def handle(self, *args, **kwargs):

        self.stdout.write("Clearing old data...")

        models = [
            SiteVisit,
            CommunicationLog,
            TrainingEngagement,
            TrainingProgram,
            MarketingCampaign,
            Task,
            Competitor,
            ChurnAlert,
            ClientContact,
            ClientOrganization,
        ]

        for m in models:
            m.objects.all().delete()

        self.stdout.write("Seeding organizations...")

        orgs = []
        for i in range(20):
            org = ClientOrganization.objects.create(
                name=fake.company(),
                legal_name=fake.company(),
                organization_type=random.choice([
                    "university", "polytechnic", "training_college",
                    "corporate", "government", "ngo", "other"
                ]),
                industry_sector=fake.job(),
                sub_sector=fake.word(),
                country="Zimbabwe",
                province=fake.state(),
                city=fake.city(),
                physical_address=fake.address(),
                website=fake.url(),
                primary_email=fake.email(),
                primary_phone=fake.phone_number(),
                size_estimate=random.randint(10, 500),
                annual_training_budget=random.uniform(10000, 100000),
                relationship_start_date=fake.date_between("-3y", "-1y"),
                relationship_status=random.choice(["prospect", "active", "at_risk"]),
                churn_risk_score=random.uniform(0, 1),
                lifetime_value_estimate=random.uniform(5000, 50000),
                notes=fake.sentence(),
            )
            orgs.append(org)

        self.stdout.write("Seeding contacts...")

        contacts = []
        for org in orgs:
            for _ in range(random.randint(1, 3)):
                contact = ClientContact.objects.create(
                    organization=org,
                    first_name=fake.first_name(),
                    last_name=fake.last_name(),
                    job_title=fake.job(),
                    department=fake.word(),
                    seniority_level=random.choice(["junior", "mid", "senior"]),
                    email=fake.email(),
                    phone=fake.phone_number(),
                    decision_maker=random.choice([True, False]),
                    primary_contact=random.choice([True, False]),
                    engagement_score=random.uniform(0, 100),
                    last_interaction_date=fake.date_between("-6m", "today"),
                    satisfaction_rating=random.uniform(1, 5),
                    notes=fake.sentence(),
                )
                contacts.append(contact)

        self.stdout.write("Seeding training programs...")

        programs = []
        for i in range(10):
            program = TrainingProgram.objects.create(
                title=fake.catch_phrase(),
                category=fake.word(),
                delivery_mode=random.choice(["online", "onsite", "hybrid"]),
                description=fake.text(),
                duration_days=random.randint(1, 30),
                cost_per_participant=random.uniform(100, 2000),
                certification_awarded=random.choice([True, False]),
                accreditation_body=fake.company(),
                target_audience=fake.text(),
                learning_objectives=fake.text(),
                active=True,
            )
            programs.append(program)

        self.stdout.write("Seeding training engagements...")

        engagements = []
        for org in orgs:
            for _ in range(random.randint(1, 3)):
                engagement = TrainingEngagement.objects.create(
                    organization=org,
                    program=random.choice(programs),
                    cohort_name=f"Cohort {random.randint(1,100)}",
                    start_date=fake.date_between("-1y", "today"),
                    end_date=fake.date_between("today", "+6m"),
                    participants_count=random.randint(5, 100),
                    completion_rate=random.uniform(50, 100),
                    average_attendance_rate=random.uniform(50, 100),
                    engagement_index=random.uniform(0, 100),
                    satisfaction_score=random.uniform(1, 5),
                    net_promoter_score=random.uniform(-100, 100),
                    customized_content_requested=random.choice([True, False]),
                    renewal_expected=random.choice([True, False]),
                    renewal_probability=random.uniform(0, 1),
                    revenue_generated=random.uniform(1000, 50000),
                    churn_flag=random.choice([True, False]),
                    churn_reason=fake.sentence(),
                    internal_notes=fake.sentence(),
                )
                engagements.append(engagement)

        self.stdout.write("Seeding tasks...")

        tasks = []
        for org in orgs:
            for _ in range(random.randint(2, 6)):
                task = Task.objects.create(
                    title=fake.sentence(),
                    description=fake.text(),
                    assigned_to=random.choice(contacts).organization.account_manager
                    if contacts else None,
                    related_organization=org,
                    due_date=fake.date_between("-10d", "+30d"),
                    completed_at=None,
                    priority=random.choice(["low", "medium", "high"]),
                    status=random.choice(["pending", "in_progress", "completed", "overdue"]),
                )
                tasks.append(task)

        self.stdout.write("Seeding churn alerts...")

        for org in orgs:
            if random.choice([True, False]):
                ChurnAlert.objects.create(
                    organization=org,
                    risk_score=random.uniform(0, 1),
                    risk_level=random.choice(["LOW", "MEDIUM", "HIGH"]),
                    trigger_reason=fake.sentence(),
                    recommended_action=fake.sentence(),
                    acknowledged=random.choice([True, False]),
                    resolved=random.choice([True, False]),
                )

        self.stdout.write("Seeding competitors...")

        for i in range(10):
            Competitor.objects.create(
                name=fake.company(),
                country="Zimbabwe",
                service_focus=fake.text(),
                pricing_notes=fake.text(),
                strengths=fake.text(),
                weaknesses=fake.text(),
                threat_level=random.uniform(0, 1),
                market_share_estimate=random.uniform(1, 50),
            )

        self.stdout.write("Seeding marketing campaigns...")

        for i in range(10):
            MarketingCampaign.objects.create(
                name=fake.catch_phrase(),
                campaign_type=random.choice(["digital", "event", "email", "sms"]),
                start_date=fake.date_between("-6m", "today"),
                end_date=fake.date_between("today", "+6m"),
                target_segment=fake.text(),
                budget=random.uniform(1000, 50000),
                leads_generated=random.randint(0, 200),
                conversions=random.randint(0, 50),
                engagement_rate=random.uniform(0, 100),
                roi_estimate=random.uniform(-50, 200),
                notes=fake.text(),
            )

        self.stdout.write("Seeding communications...")

        for org in orgs:
            for _ in range(random.randint(1, 5)):
                CommunicationLog.objects.create(
                    organization=org,
                    contact=random.choice(contacts) if contacts else None,
                    channel=random.choice(["email", "phone", "meeting", "sms", "whatsapp"]),
                    subject=fake.sentence(),
                    interaction_summary=fake.text(),
                    sentiment_score=random.uniform(-1, 1),
                    response_received=random.choice([True, False]),
                    response_time_hours=random.uniform(0, 72),
                    follow_up_required=random.choice([True, False]),
                    follow_up_date=fake.date_between("today", "+30d"),
                )

        self.stdout.write("Seeding site visits...")

        for i in range(100):
            SiteVisit.objects.create(
                user=None,
                session_key=fake.uuid4(),
                is_authenticated=False,
                organization=random.choice(orgs),
                visit_type=random.choice([
                    "page_view", "login", "logout", "api_call", "form_submit"
                ]),
                path=fake.uri_path(),
                view_name="",
                http_method="GET",
                timestamp=fake.date_time_between("-1y", "now"),
                duration_seconds=random.uniform(1, 300),
                ip_address=fake.ipv4(),
                user_agent=fake.user_agent(),
                device_type=random.choice(["mobile", "desktop"]),
                browser=fake.word(),
                os=fake.word(),
                referrer=fake.url(),
                is_bounce=random.choice([True, False]),
                converted=random.choice([True, False]),
            )

        self.stdout.write(self.style.SUCCESS("Database successfully seeded!"))