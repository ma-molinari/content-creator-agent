import unittest

from summarize_job_metrics import summarize


class MetricsSummaryTest(unittest.TestCase):
    def test_aggregates_valid_events_without_sensitive_fields(self):
        lines = [
            'prefix [metrics] event=job_terminal job_id=secret format=structured_v1 outcome=done code=NONE duration_ms=100',
            'prefix [metrics] event=job_terminal job_id=other format=structured_v1 outcome=conflict code=VERSION_CONFLICT duration_ms=300',
            'prefix [metrics] event=job_terminal format=legacy_html outcome=failed code=STUCK_PROCESSING duration_ms=200',
            'prefix [metrics] event=artifact_cleanup outcome=done objects=3',
            'prefix [metrics] event=artifact_cleanup outcome=failed objects=2',
            'prefix [metrics] event=stuck_job_cleanup outcome=done jobs=1 threshold_minutes=20',
            'prefix [metrics] event=stuck_job_cleanup outcome=failed',
            'prefix [metrics] event=job_terminal format=structured_v1 outcome=done duration_ms=invalid',
            'prefix [metrics] event=artifact_cleanup outcome=done objects=-1',
            'unrelated log content=private',
        ]
        result = summarize(lines)
        self.assertEqual(result['jobs']['structured_v1'], {'done': 1, 'failed': 0, 'conflict': 1, 'total': 2, 'duration_p95_ms': 300})
        self.assertEqual(result['jobs']['legacy_html']['failed'], 1)
        self.assertEqual(result['cleanup'], {'done_batches': 1, 'failed_batches': 1, 'attempted_objects': 5})
        self.assertEqual(result['watchdog'], {'done_runs': 1, 'failed_runs': 1, 'jobs': 1})
        self.assertNotIn('secret', str(result))
        self.assertNotIn('private', str(result))

    def test_empty_input_has_no_percentile(self):
        self.assertIsNone(summarize([])['jobs']['structured_v1']['duration_p95_ms'])


if __name__ == '__main__':
    unittest.main()
