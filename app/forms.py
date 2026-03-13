# forms.py
from django import forms
from .models import Task

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "description", "assigned_to", "related_organization", "due_date", "priority", "status"]
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "priority": forms.TextInput(attrs={"class": "form-control"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "assigned_to": forms.Select(attrs={"class": "form-select"}),
            "related_organization": forms.Select(attrs={"class": "form-select"}),
        }


from django import forms
from .models import ChurnAlert

class ChurnAlertForm(forms.ModelForm):
    class Meta:
        model = ChurnAlert
        fields = ["organization", "trigger_reason", "recommended_action", "acknowledged", "resolved"]
        widgets = {
            "trigger_reason": forms.Textarea(attrs={"rows": 3}),
            "recommended_action": forms.Textarea(attrs={"rows": 3}),
        }
        
        
from django import forms
from .models import TrainingProgram


class TrainingProgramForm(forms.ModelForm):

    class Meta:
        model = TrainingProgram
        fields = "__all__"

        widgets = {

            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Program title"
            }),

            "category": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Category"
            }),

            "delivery_mode": forms.Select(
                choices=[
                    ("online", "Online"),
                    ("onsite", "Onsite"),
                    ("hybrid", "Hybrid")
                ],
                attrs={"class": "form-control"}
            ),

            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3
            }),

            "duration_days": forms.NumberInput(attrs={
                "class": "form-control"
            }),

            "cost_per_participant": forms.NumberInput(attrs={
                "class": "form-control"
            }),

            "certification_awarded": forms.CheckboxInput(attrs={
                "class": "form-check-input"
            }),

            "accreditation_body": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Accreditation body"
            }),

            "target_audience": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3
            }),

            "learning_objectives": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3
            }),

            "active": forms.CheckboxInput(attrs={
                "class": "form-check-input"
            }),

        }
        
        
from django import forms
from .models import TrainingEngagement

class TrainingEngagementForm(forms.ModelForm):

    class Meta:
        model = TrainingEngagement
        fields = "__all__"

        widgets = {

            "organization": forms.Select(attrs={"class": "form-control"}),

            "program": forms.Select(attrs={"class": "form-control"}),

            "cohort_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Cohort Name"
            }),

            "start_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),

            "end_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),

            "participants_count": forms.NumberInput(attrs={"class": "form-control"}),

            "completion_rate": forms.NumberInput(attrs={"class": "form-control"}),

            "average_attendance_rate": forms.NumberInput(attrs={"class": "form-control"}),

            "engagement_index": forms.NumberInput(attrs={"class": "form-control"}),

            "satisfaction_score": forms.NumberInput(attrs={"class": "form-control"}),

            "net_promoter_score": forms.NumberInput(attrs={"class": "form-control"}),

            "renewal_probability": forms.NumberInput(attrs={"class": "form-control"}),

            "revenue_generated": forms.NumberInput(attrs={"class": "form-control"}),

            "customization_details": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3
            }),

            "churn_reason": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3
            }),

            "internal_notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3
            }),

            "customized_content_requested": forms.CheckboxInput(attrs={"class": "form-check-input"}),

            "renewal_expected": forms.CheckboxInput(attrs={"class": "form-check-input"}),

            "churn_flag": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        
        
from django import forms
from .models import ClientOrganization


class ClientOrganizationForm(forms.ModelForm):

    class Meta:
        model = ClientOrganization
        fields = "__all__"

        widgets = {

            "name": forms.TextInput(attrs={"class": "form-control"}),

            "legal_name": forms.TextInput(attrs={"class": "form-control"}),

            "organization_type": forms.Select(attrs={"class": "form-control"}),

            "registration_number": forms.TextInput(attrs={"class": "form-control"}),

            "tax_number": forms.TextInput(attrs={"class": "form-control"}),

            "industry_sector": forms.TextInput(attrs={"class": "form-control"}),

            "sub_sector": forms.TextInput(attrs={"class": "form-control"}),

            "country": forms.TextInput(attrs={"class": "form-control"}),

            "province": forms.TextInput(attrs={"class": "form-control"}),

            "city": forms.TextInput(attrs={"class": "form-control"}),

            "physical_address": forms.Textarea(attrs={"class": "form-control", "rows": 3}),

            "website": forms.URLInput(attrs={"class": "form-control"}),

            "primary_email": forms.EmailInput(attrs={"class": "form-control"}),

            "primary_phone": forms.TextInput(attrs={"class": "form-control"}),

            "size_estimate": forms.NumberInput(attrs={"class": "form-control"}),

            "annual_training_budget": forms.NumberInput(attrs={"class": "form-control"}),

            "relationship_start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),

            "relationship_status": forms.Select(attrs={"class": "form-control"}),

            "account_manager": forms.Select(attrs={"class": "form-control"}),

            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }