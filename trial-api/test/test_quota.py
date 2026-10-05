import pathlib
import sqlite3
import unittest


MIGRATION = pathlib.Path(__file__).parents[1] / "migrations" / "0001_init.sql"


class QuotaAccountingTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.executescript(MIGRATION.read_text())
        self.db.execute("INSERT INTO trial_records(record_id, company_id, verified_at) VALUES ('r1', 'situsnap-trial', 1)")
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def reservation(self, photo_id="p1", slot=1, size=100):
        self.db.execute("""INSERT INTO photos
            (photo_id, record_id, slot, content_type, byte_size, object_key, state, uploaded_by, uploaded_at, reservation_expires_at)
            VALUES (?, 'r1', ?, 'image/jpeg', ?, ?, 'reserved', 'user-hash', 1, 100)""",
            (photo_id, slot, size, f"trial/{photo_id}"))
        self.db.commit()

    def usage(self):
        return self.db.execute("SELECT used_bytes, reserved_bytes FROM storage_usage WHERE singleton=1").fetchone()

    def test_reserved_bytes_count_immediately_and_release_on_rejected_upload(self):
        self.reservation(size=400)
        self.assertEqual(self.usage(), (0, 400))
        self.db.execute("DELETE FROM photos WHERE photo_id='p1'")
        self.db.commit()
        self.assertEqual(self.usage(), (0, 0))

    def test_success_moves_reservation_to_used_and_confirmed_delete_frees_it(self):
        self.reservation(size=500)
        self.db.execute("UPDATE photos SET state='stored', reservation_expires_at=NULL, screened_by='screen-v1' WHERE photo_id='p1'")
        self.db.commit()
        self.assertEqual(self.usage(), (500, 0))
        self.db.execute("DELETE FROM photos WHERE photo_id='p1'")
        self.db.commit()
        self.assertEqual(self.usage(), (0, 0))

    def test_reservation_cannot_cross_the_7_gb_cap_even_at_boundary(self):
        self.db.execute("UPDATE storage_usage SET used_bytes=6999999000 WHERE singleton=1")
        self.db.commit()
        self.reservation(size=1000)
        self.assertEqual(self.usage(), (6999999000, 1000))
        with self.assertRaisesRegex(sqlite3.IntegrityError, "trial storage full"):
            self.db.execute("""INSERT INTO photos
                (photo_id, record_id, slot, content_type, byte_size, object_key, state, uploaded_by, uploaded_at, reservation_expires_at)
                VALUES ('p2','r1',2,'image/jpeg',1,'trial/p2','reserved','user-hash',1,100)""")

    def test_unique_two_slots_rejects_a_third_photo(self):
        self.reservation(slot=1, photo_id="p1")
        self.reservation(slot=2, photo_id="p2")
        with self.assertRaises(sqlite3.IntegrityError):
            self.reservation(slot=2, photo_id="p3")

    def test_only_reserved_to_stored_transition_is_allowed(self):
        self.reservation()
        with self.assertRaisesRegex(sqlite3.IntegrityError, "invalid photo transition"):
            self.db.execute("UPDATE photos SET byte_size=200 WHERE photo_id='p1'")
        with self.assertRaisesRegex(sqlite3.IntegrityError, "invalid photo transition"):
            self.db.execute("UPDATE photos SET state='reserved', reservation_expires_at=99 WHERE photo_id='p1'")

    def test_unverified_record_cannot_receive_a_photo(self):
        self.db.execute("INSERT INTO trial_records(record_id,company_id,verified_at) VALUES ('r2','situsnap-trial',NULL)")
        with self.assertRaisesRegex(sqlite3.IntegrityError, "verified record required"):
            self.db.execute("""INSERT INTO photos
                (photo_id, record_id, slot, content_type, byte_size, object_key, state, uploaded_by, uploaded_at, reservation_expires_at)
                VALUES ('p1','r2',1,'image/jpeg',1,'trial/p1','reserved','user-hash',1,100)""")


if __name__ == "__main__":
    unittest.main()
