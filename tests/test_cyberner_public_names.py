import unittest
from unittest.mock import patch
import test_identity_projection as fixture
from cyberner_presentation import labels


class PublicNamesTests(unittest.TestCase):
    setUp = fixture.UserIdentityProjectionTests.setUp
    tearDown = fixture.UserIdentityProjectionTests.tearDown

    def test_history_contacts_and_rename_keep_account_ids(self):
        account='id_98db6570c9dee8dcd3'
        created=self.users.save_profile_guarded(fixture.build_profile(account,nick='Neo'),
            expected_revision=0,source='test.chat',allow_create=True)
        original={'sender':account,'body':'hello','safety_key':'unchanged'}
        rows=labels([original,{'sender':'System'},{'sender':'deleted-user'}],self.identities)
        self.assertEqual(rows[0]['sender_display_name'],'Neo')
        self.assertEqual(rows[0]['sender'],account)
        self.assertEqual(rows[0]['safety_key'],'unchanged')
        self.assertNotIn('sender_display_name',original)
        self.assertEqual(rows[1]['sender_display_name'],'System')
        self.assertEqual(rows[2]['sender_display_name'],'deleted-user')
        self.assertEqual(labels([{'name':account}],self.identities,'name','display_name')[0],
            {'name':account,'display_name':'Neo'})
        self.users.patch_profile_guarded(account,{'nick':'Trinity'},source='test.rename',
            expected_revision=created['profile_revision'])
        self.assertEqual(labels([original],self.identities)[0]['sender_display_name'],'Trinity')

    def test_live_event_and_notifications_preserve_identity(self):
        import run
        account='id_oauth_fixture'
        self.users.save_profile_guarded(fixture.build_profile(account,nick='Neo'),
            expected_revision=0,source='test.chat',allow_create=True)
        route=dict(channel='world',channel_key='world',source='world',scope='group',peer='global')
        with patch.object(run,'identity_projection_store',self.identities):
            event=run.canonical_cyberner_message({'sender':account,'body':'hello'},route)
            self.assertEqual(event['sender'],account)
            self.assertEqual(event['sender_display_name'],'Neo')
            self.assertEqual(run.cyberner_notification_title('player','direct',account,account),'Neo')
