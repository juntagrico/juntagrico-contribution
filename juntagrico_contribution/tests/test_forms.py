from juntagrico_contribution.forms import ContributionSelectionForm
from juntagrico_contribution.models import ContributionSelection
from . import ContributionTestCase, AssignmentMixin


class AssignmentValidationTests(AssignmentMixin, ContributionTestCase):
    def get_form(self, total, core):
        return ContributionSelectionForm(self.contribution_round, self.sub, {
            'selection': self.option2.pk,
            'total_assignments': total,
            'core_assignments': core,
        })

    def test_valid(self):
        form = self.get_form(10, 5)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        contribution = self.sub.contributions.first()
        self.assertEqual(contribution.selected_option, self.option2)
        self.assertEqual(contribution.total_assignments, 10)
        self.assertEqual(contribution.core_assignments, 5)

    def test_total_too_low(self):
        form = self.get_form(9, 5)
        self.assertFalse(form.is_valid())
        self.assertIn('total_assignments', form.errors)
        self.assertNotIn('core_assignments', form.errors)

    def test_core_too_low(self):
        form = self.get_form(10, 4)
        self.assertFalse(form.is_valid())
        self.assertIn('core_assignments', form.errors)
        self.assertNotIn('total_assignments', form.errors)

    def test_both_too_low(self):
        form = self.get_form(9, 4)
        self.assertFalse(form.is_valid())
        self.assertIn('total_assignments', form.errors)
        self.assertIn('core_assignments', form.errors)

    def test_core_too_low_not_stored(self):
        form = self.get_form(10, 4)
        self.assertFalse(form.is_valid())
        selection = ContributionSelection.objects.get(round=self.contribution_round, subscription=self.sub)
        self.assertEqual(selection.core_assignments, 5)
