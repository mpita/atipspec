import json
from pathlib import Path

from atipspec.deliver import merge_requirements
from atipspec.delivery import parse_spec
from atipspec.errors import AtipSpecError
from atipspec.project import Project
from atipspec.traceability import next_ids, merge_conflicts
from atipspec.pilot import initialize, record, pilot_report
from tests.helpers import ProjectCase


class TraceabilityTests(ProjectCase):
    def test_rename_preserves_ids_and_duplicate_title_is_separate(self):
        current = '# auth\n\n### REQ-001: Old title\n- AC-001: original\n'
        change = parse_spec('# auth\n\n### REQ-001: New title\n- AC-001: improved\n\n### REQ-002: New title\n- AC-002: distinct\n')
        merged = merge_requirements(current, change.requirements)
        self.assertEqual(len(parse_spec(merged).requirements), 2)
        self.assertNotIn("Old title", merged)
        self.assertIn("AC-001: improved", merged)

    def test_stable_ids_are_required_and_next_ids_do_not_reset(self):
        project = Project.find(self.root)
        living = project.specs / 'auth.md'
        living.write_text('# auth\n\n### Login\n\nAcceptance criteria:\n- logs in\n')
        with self.assertRaises(AtipSpecError):
            merge_requirements(living.read_text(), [])
        living.write_text("# auth\n\n### REQ-001: Login\n- AC-001: logs in\n")
        self.assertEqual(next_ids(project, 'auth'), (2, 2))
        self.new_delivery()
        self.assertNotIn('### REQ-', (self.delivery() / 'spec.md').read_text(),
                         'guided deliveries reference canonical requirements without empty definitions')
        self.assertEqual(next_ids(project, 'auth'), (2, 2))

    def test_parallel_requirement_collision_is_detected(self):
        project = Project.find(self.root)
        self.new_delivery()
        self.write_spec()
        (project.specs / 'auth.md').write_text('# auth\n\n### REQ-001: Another delivery\n- AC-001: other\n')
        problems = merge_conflicts(project, parse_spec((self.delivery() / 'spec.md').read_text()))
        self.assertTrue(any('REQ-001 changed' in p for p in problems))

    def test_pilot_never_invents_missing_observations(self):
        project = Project.find(self.root)
        initialize(project, 'quality')
        self.assertEqual(pilot_report(project, 'quality')['observations'], 0)
        metrics = dict(lead_hours=4, human_review_minutes=20, rework_minutes=10,
                       escaped_defects=1, criteria_total=4, criteria_tested=3, observation_days=14)
        record(project, 'quality', 'one', 'baseline', metrics, 'ticket:1', 'qa')
        record(project, 'quality', 'two', 'atipspec', {**metrics, 'escaped_defects': 0}, 'ticket:2', 'qa')
        result = pilot_report(project, 'quality')
        self.assertTrue(result['comparable_observation_windows'])
        self.assertEqual(result['cohorts']['baseline']['tested_criteria_fraction'], .75)
        with self.assertRaises(AtipSpecError):
            record(project, 'quality', 'one', 'baseline', metrics, 'ticket:1', 'qa')
        with self.assertRaises(AtipSpecError):
            record(project, 'quality', 'bad', 'atipspec', {**metrics, 'criteria_tested': 9}, 'ticket:3', 'qa')
