import random
from django.core.management.base import BaseCommand
from faker import Faker
from app.models import *

fake = Faker("en_GB")


# ----------------------------
# ZIMBABWE DATASETS
# ----------------------------

ZIM_PROVINCES = [
    "Harare","Bulawayo","Manicaland","Mashonaland East",
    "Mashonaland West","Mashonaland Central","Masvingo",
    "Matabeleland North","Matabeleland South","Midlands"
]

ZIM_CITIES = [
    "Harare","Bulawayo","Mutare","Gweru","Kwekwe",
    "Masvingo","Chinhoyi","Marondera","Kadoma",
    "Victoria Falls","Bindura","Redcliff"
]

ZIM_ORGANIZATIONS = [
    "University of Zimbabwe",
    "National University of Science and Technology",
    "Midlands State University",
    "Chinhoyi University of Technology",
    "Zimbabwe Open University",
    "Econet Wireless Zimbabwe",
    "NetOne Zimbabwe",
    "CBZ Holdings",
    "Stanbic Bank Zimbabwe",
    "Delta Corporation",
    "Old Mutual Zimbabwe",
    "OK Zimbabwe",
    "Zimbabwe Revenue Authority",
    "Ministry of ICT Zimbabwe",
    "Zimbabwe Electricity Supply Authority",
    "SeedCo Zimbabwe",
    "Innscor Africa",
    "Zimnat Insurance",
    "CABS Bank",
    "FBC Holdings"
]

ZIM_FIRST_NAMES = [
    "Tawanda","Tendai","Tatenda","Nyasha","Ruvimbo","Blessing",
    "Simbarashe","Tapiwa","Tariro","Farai","Kudakwashe",
    "Rutendo","Panashe","Tanaka","Chipo","Precious"
]

ZIM_LAST_NAMES = [
    "Moyo","Ndlovu","Dube","Sibanda","Mpofu","Chikowore",
    "Mutasa","Gumbo","Zhou","Chirisa","Mlambo",
    "Shumba","Banda","Phiri","Nyathi","Chakabva"
]

TASK_TITLES = [
    "Follow up training proposal",
    "Schedule client meeting",
    "Send training quotation",
    "Prepare training materials",
    "Discuss contract renewal",
    "Review training feedback",
    "Confirm participant list",
    "Organize training venue"
]

CHURN_REASONS = [
    "Client budget constraints",
    "Competitor offered lower pricing",
    "Training program postponed",
    "Low engagement from participants",
    "Management restructuring"
]

PROGRAMS = [
    "Data Analytics for Business",
    "Cybersecurity Fundamentals",
    "Project Management Professional Prep",
    "Digital Transformation Strategy",
    "Leadership & Management Excellence",
    "AI for Business Leaders",
    "Cloud Computing Essentials",
    "Python for Data Science",
    "Business Intelligence with Power BI",
    "Agile & Scrum Master Training"
]


class Command(BaseCommand):

    help = "Seed CRM system with Zimbabwe demo data"

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

        # -------------------------
        # ORGANIZATIONS
        # -------------------------

        self.stdout.write("Seeding organizations...")

        orgs = []

        for name in ZIM_ORGANIZATIONS:

            org = ClientOrganization.objects.create(
                name=name,
                legal_name=name,
                organization_type=random.choice([
                    "university","corporate","government","ngo"
                ]),
                industry_sector=random.choice([
                    "Education","Finance","Telecommunications",
                    "Government","Retail","Agriculture","Energy"
                ]),
                sub_sector="Training & Development",
                country="Zimbabwe",
                province=random.choice(ZIM_PROVINCES),
                city=random.choice(ZIM_CITIES),
                physical_address=f"{random.randint(1,200)} {fake.street_name()}",
                website=f"https://www.{name.replace(' ','').lower()}.co.zw",
                primary_email=f"info@{name.replace(' ','').lower()}.co.zw",
                primary_phone=f"+2637{random.randint(10000000,99999999)}",
                size_estimate=random.randint(30,350),
                annual_training_budget=random.uniform(2000,40000),
                relationship_start_date=fake.date_between("-3y","-1y"),
                relationship_status=random.choice(["prospect","active","at_risk"]),
                churn_risk_score=random.uniform(0.05,0.65),
                lifetime_value_estimate=random.uniform(8000,120000),
                notes=fake.sentence()
            )

            orgs.append(org)

        # -------------------------
        # CONTACTS
        # -------------------------

        self.stdout.write("Seeding contacts...")

        contacts = []

        for org in orgs:

            for _ in range(random.randint(2,4)):

                first = random.choice(ZIM_FIRST_NAMES)
                last = random.choice(ZIM_LAST_NAMES)

                contact = ClientContact.objects.create(
                    organization=org,
                    first_name=first,
                    last_name=last,
                    job_title=random.choice([
                        "HR Manager","Training Manager",
                        "Learning & Development Officer",
                        "IT Director","Operations Manager"
                    ]),
                    department=random.choice(["HR","Training","IT","Operations"]),
                    seniority_level=random.choice(["mid","senior"]),
                    email=f"{first.lower()}.{last.lower()}@{org.website.replace('https://www.','')}",
                    phone=f"+2637{random.randint(10000000,99999999)}",
                    decision_maker=random.choice([True,False]),
                    primary_contact=random.choice([True,False]),
                    engagement_score=random.uniform(35,95),
                    last_interaction_date=fake.date_between("-6m","today"),
                    satisfaction_rating=random.uniform(3.2,4.8),
                    notes=fake.sentence()
                )

                contacts.append(contact)

        # -------------------------
        # TRAINING PROGRAMS
        # -------------------------

        self.stdout.write("Seeding programs...")

        programs = []

        for title in PROGRAMS:

            program = TrainingProgram.objects.create(
                title=title,
                category="Professional Training",
                delivery_mode=random.choice(["online","onsite","hybrid"]),
                description=fake.text(),
                duration_days=random.randint(2,10),
                cost_per_participant=random.uniform(150,1200),
                certification_awarded=random.choice([True,False]),
                accreditation_body="Zimbabwe Institute of Management",
                target_audience="Professionals and managers",
                learning_objectives=fake.text(),
                active=True
            )

            programs.append(program)

        # -------------------------
        # TRAINING ENGAGEMENTS
        # -------------------------

        self.stdout.write("Seeding engagements...")

        for org in orgs:

            for _ in range(random.randint(1,3)):

                TrainingEngagement.objects.create(
                    organization=org,
                    program=random.choice(programs),
                    cohort_name=f"Cohort {random.randint(1,100)}",
                    start_date=fake.date_between("-1y","today"),
                    end_date=fake.date_between("today","+3m"),
                    participants_count=random.randint(8,45),
                    completion_rate=random.uniform(75,98),
                    average_attendance_rate=random.uniform(70,96),
                    engagement_index=random.uniform(55,92),
                    satisfaction_score=random.uniform(3.5,4.9),
                    net_promoter_score=random.uniform(10,65),
                    customized_content_requested=random.choice([True,False]),
                    renewal_expected=random.choice([True,False]),
                    renewal_probability=random.uniform(0.35,0.85),
                    revenue_generated=random.uniform(1800,28000),
                    churn_flag=random.choice([False,False,True]),
                    churn_reason=random.choice(CHURN_REASONS),
                    internal_notes=fake.sentence()
                )

        # -------------------------
        # TASKS
        # -------------------------

        self.stdout.write("Seeding tasks...")

        for org in orgs:

            for _ in range(random.randint(2,5)):

                Task.objects.create(
                    title=random.choice(TASK_TITLES),
                    description=fake.sentence(),
                    assigned_to=None,
                    related_organization=org,
                    due_date=fake.date_between("-5d","+20d"),
                    completed_at=None,
                    priority=random.choice(["low","medium","high"]),
                    status=random.choice([
                        "pending","in_progress","completed","overdue"
                    ])
                )

        # -------------------------
        # CHURN ALERTS
        # -------------------------

        self.stdout.write("Seeding churn alerts...")

        for org in orgs:

            if random.random() < 0.35:

                risk = random.uniform(0.2,0.75)

                if risk > 0.6:
                    level = "HIGH"
                elif risk > 0.4:
                    level = "MEDIUM"
                else:
                    level = "LOW"

                ChurnAlert.objects.create(
                    organization=org,
                    risk_score=risk,
                    risk_level=level,
                    trigger_reason=random.choice(CHURN_REASONS),
                    recommended_action=random.choice([
                        "Schedule client meeting",
                        "Offer customized training package",
                        "Provide renewal discount",
                        "Increase engagement"
                    ]),
                    acknowledged=random.choice([True,False]),
                    resolved=random.choice([False,False,True])
                )

        # -------------------------
        # COMPETITORS
        # -------------------------

        COMPETITORS = [
            "Speciss College",
            "Zimbabwe Institute of Management",
            "Trust Academy",
            "Digital Skills Africa",
            "Africa University Training Centre",
            "UZ Professional Development Centre"
        ]

        for c in COMPETITORS:

            Competitor.objects.create(
                name=c,
                country="Zimbabwe",
                service_focus="Professional training",
                pricing_notes="Competitive pricing",
                strengths="Strong corporate partnerships",
                weaknesses="Limited digital delivery",
                threat_level=random.uniform(0.15,0.75),
                market_share_estimate=random.uniform(2,18)
            )

        # -------------------------
        # MARKETING CAMPAIGNS
        # -------------------------

        for i in range(8):

            MarketingCampaign.objects.create(
                name=f"{random.choice(['AI','Cloud','Data'])} Training Campaign",
                campaign_type=random.choice(["digital","email","event"]),
                start_date=fake.date_between("-6m","today"),
                end_date=fake.date_between("today","+3m"),
                target_segment="Corporate organizations",
                budget=random.uniform(500,12000),
                leads_generated=random.randint(10,120),
                conversions=random.randint(3,35),
                engagement_rate=random.uniform(5,35),
                roi_estimate=random.uniform(10,120),
                notes="Corporate outreach campaign"
            )

        # -------------------------
        # COMMUNICATION LOGS
        # -------------------------

        for org in orgs:

            for _ in range(random.randint(1,4)):

                CommunicationLog.objects.create(
                    organization=org,
                    contact=random.choice(contacts),
                    channel=random.choice([
                        "email","phone","meeting","sms","whatsapp"
                    ]),
                    subject=fake.sentence(),
                    interaction_summary=fake.text(),
                    sentiment_score=random.uniform(-0.4,0.9),
                    response_received=random.choice([True,False]),
                    response_time_hours=random.uniform(2,48),
                    follow_up_required=random.choice([True,False]),
                    follow_up_date=fake.date_between("today","+20d")
                )

        # -------------------------
        # SITE VISITS
        # -------------------------

        self.stdout.write("Seeding analytics visits...")

        for i in range(120):

            SiteVisit.objects.create(
                user=None,
                session_key=fake.uuid4(),
                is_authenticated=False,
                organization=random.choice(orgs),
                visit_type=random.choice([
                    "page_view","login","logout","form_submit"
                ]),
                path="/dashboard/",
                view_name="dashboard",
                http_method="GET",
                timestamp=fake.date_time_between("-1y","now"),
                duration_seconds=random.uniform(15,220),
                ip_address=fake.ipv4(),
                user_agent=fake.user_agent(),
                device_type=random.choice(["mobile","desktop"]),
                browser=random.choice(["Chrome","Edge","Firefox"]),
                os=random.choice(["Windows","Android","MacOS"]),
                referrer="https://google.com",
                is_bounce=random.choice([True,False]),
                converted=random.choice([True,False])
            )

        self.stdout.write(self.style.SUCCESS("Zimbabwe CRM dataset seeded successfully!"))