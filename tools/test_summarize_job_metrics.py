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
            'prefix [metrics] event=artifact_reconcile outcome=done inventories=2 failed_jobs=1 prefixes=3 pages=2 listed_objects=4 reference_queries=8 delete_calls=2 attempted_objects=4 duration_ms=1000',
            'prefix [metrics] event=job_terminal format=structured_v1 outcome=done duration_ms=invalid',
            'prefix [metrics] event=artifact_cleanup outcome=done objects=-1',
            'unrelated log content=private',
        ]
        result = summarize(lines)
        self.assertEqual(result['jobs']['structured_v1'], {'done': 1, 'failed': 0, 'conflict': 1, 'total': 2, 'duration_p95_ms': 300})
        self.assertEqual(result['jobs']['legacy_html']['failed'], 1)
        self.assertEqual(result['cleanup'], {'done_batches': 1, 'failed_batches': 1, 'attempted_objects': 5})
        self.assertEqual(result['watchdog'], {'done_runs': 1, 'failed_runs': 1, 'jobs': 1})
        self.assertEqual(result['reconcile']['inventories'], 2)
        self.assertEqual(result['reconcile']['listed_objects'], 4)
        self.assertEqual(result['reconcile']['duration_p95_ms'], 1000)
        self.assertNotIn('secret', str(result))
        self.assertNotIn('private', str(result))

    def test_empty_input_has_no_percentile(self):
        self.assertIsNone(summarize([])['jobs']['structured_v1']['duration_p95_ms'])

    def test_visual_events_are_aggregated_without_exposing_content(self):
        lines = [
            '[metrics] event=visual_direction schema=2 outcome=success duration_ms=100 decorations=2 prompt=secret',
            '[metrics] event=visual_direction schema=2 outcome=failed reason=fetch duration_ms=200 image=private',
            '[metrics] event=structured_validation schema=2 outcome=failed reason=contrast duration_ms=5',
            '[metrics] event=structured_render schema=2 outcome=failed reason=overflow duration_ms=10',
            '[metrics] event=structured_publication schema=2 outcome=unknown',
            '[metrics] event=worker_capability schema_version=2 outcome=unavailable',
            '[metrics] event=structured_render schema=2 outcome=success duration_ms=-1',
            '[metrics] event=structured_render schema=1 outcome=success duration_ms=5',
            '[metrics] event=structured_execution schema=2 outcome=failed reason=secret',
        ]
        result = summarize(lines)['visual_v2']
        self.assertEqual(result['visual_direction']['outcomes']['success'], 1)
        self.assertEqual(result['visual_direction']['reasons']['fetch'], 1)
        self.assertEqual(result['visual_direction']['decorations'], 2)
        self.assertEqual(result['visual_direction']['duration_p95_ms'], 200)
        self.assertEqual(result['structured_validation']['reasons']['contrast'], 1)
        self.assertEqual(result['structured_render']['reasons']['overflow'], 1)
        self.assertEqual(result['structured_render']['outcomes']['success'], 0)
        self.assertEqual(result['structured_publication']['outcomes']['unknown'], 1)
        self.assertEqual(result['worker_capability']['outcomes']['unavailable'], 1)
        self.assertNotIn('secret', str(result))
        self.assertNotIn('private', str(result))


if __name__ == '__main__':
    unittest.main()
