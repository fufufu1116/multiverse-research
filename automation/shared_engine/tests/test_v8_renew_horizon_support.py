import os
import tempfile
import unittest
from unittest.mock import patch

import config
import db


class RenewHorizonSupportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        config.DB_PATH = os.path.join(self.tmp.name, 'shared.db')
        db.init_schema()

    def tearDown(self):
        self.tmp.cleanup()

    def _active(self):
        with patch.object(db.time, 'time', return_value=1000.0):
            task_id = db.create_task('core', 'renew horizon support', task_type='implement')
            generation = db.claim_task(task_id, 'worker-1', lease_seconds=120)
        with patch.object(db.time, 'time', return_value=1000.1):
            db.transition(task_id, 'IN_IMPLEMENT', actor='support', event_type='START', fencing=('worker-1', generation))
        return task_id, generation

    def test_rapid_renewals_do_not_accumulate_duration_per_call(self):
        task_id, generation = self._active()
        initial_until = db.get_task(task_id)['lease_until']
        self.assertEqual(initial_until, 1120.0)

        renew_times = [1000.2, 1000.3, 1000.4, 1000.5, 1000.6]
        observed = []
        for now in renew_times:
            with patch.object(db.time, 'time', return_value=now):
                observed.append(db.renew_lease(task_id, 'worker-1', generation, lease_seconds=120))

        final_until = db.get_task(task_id)['lease_until']
        self.assertEqual(final_until, 1120.6)
        self.assertEqual(observed[-1], 1120.6)
        self.assertLess(final_until, initial_until + 1.0)
        self.assertNotEqual(final_until, initial_until + 5 * 120)

    def test_late_renewal_extends_only_to_now_plus_bounded_duration(self):
        task_id, generation = self._active()
        with patch.object(db.time, 'time', return_value=1119.0):
            renewed_until = db.renew_lease(task_id, 'worker-1', generation, lease_seconds=120)
        self.assertEqual(renewed_until, 1239.0)
        self.assertEqual(db.get_task(task_id)['lease_until'], 1239.0)


if __name__ == '__main__':
    unittest.main()
