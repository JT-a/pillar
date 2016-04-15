# -*- encoding: utf-8 -*-

import responses
import json

from bson import ObjectId
from flask import g

from common_test_class import (AbstractPillarTest, TEST_EMAIL_ADDRESS, BLENDER_ID_TEST_USERID,
                               TEST_SUBCLIENT_TOKEN, BLENDER_ID_USER_RESPONSE, TEST_FULL_NAME)


class BlenderIdSubclientTest(AbstractPillarTest):
    @responses.activate
    def test_store_scst_new_user(self):
        self._common_user_test(201)

    @responses.activate
    def test_store_scst_existing_user(self):
        # Make sure the user exists in our database.
        from application.utils.authentication import create_new_user
        with self.app.test_request_context():
            create_new_user(TEST_EMAIL_ADDRESS, 'apekoppie', BLENDER_ID_TEST_USERID)

        self._common_user_test(200)

    @responses.activate
    def test_store_multiple_tokens(self):
        scst1 = '%s-1' % TEST_SUBCLIENT_TOKEN
        scst2 = '%s-2' % TEST_SUBCLIENT_TOKEN
        db_user1 = self._common_user_test(201, scst=scst1)
        db_user2 = self._common_user_test(200, scst=scst2)
        self.assertEqual(db_user1['_id'], db_user2['_id'])

        # Now there should be two tokens.
        with self.app.test_request_context():
            tokens = self.app.data.driver.db['tokens']
            self.assertIsNotNone(tokens.find_one({'user': db_user1['_id'], 'token': scst1}))
            self.assertIsNotNone(tokens.find_one({'user': db_user1['_id'], 'token': scst2}))

        # There should still be only one auth element for blender-id in the user doc.
        self.assertEqual(1, len(db_user1['auth']))

    @responses.activate
    def test_authenticate_with_scst(self):
        # Make sure there is a user and SCST.
        db_user = self._common_user_test(201)

        # Make a call that's authenticated with the SCST
        from application.utils import authentication as auth

        subclient_id = self.app.config['BLENDER_ID_SUBCLIENT_ID']
        auth_header = self.make_header(TEST_SUBCLIENT_TOKEN, subclient_id)

        with self.app.test_request_context(headers={'Authorization': auth_header}):
            self.assertTrue(auth.validate_token())
            self.assertIsNotNone(g.current_user)
            self.assertEqual(db_user['_id'], g.current_user['user_id'])

    def _common_user_test(self, expected_status_code, scst=TEST_SUBCLIENT_TOKEN):
        self.mock_blenderid_validate_happy()

        subclient_id = self.app.config['BLENDER_ID_SUBCLIENT_ID']
        resp = self.client.post('/blender_id/store_scst',
                                data={'user_id': BLENDER_ID_TEST_USERID,
                                      'subclient_id': subclient_id,
                                      'token': scst})
        self.assertEqual(expected_status_code, resp.status_code)

        user_info = json.loads(resp.data)  # {'status': 'success', 'subclient_user_id': '...'}
        self.assertEqual('success', user_info['status'])

        with self.app.test_request_context():
            # Check that the user was correctly updated
            users = self.app.data.driver.db['users']
            db_user = users.find_one(ObjectId(user_info['subclient_user_id']))
            self.assertIsNotNone(db_user, 'user %r not found' % user_info['subclient_user_id'])

            self.assertEqual(TEST_EMAIL_ADDRESS, db_user['email'])
            self.assertEqual(TEST_FULL_NAME, db_user['full_name'])
            # self.assertEqual(TEST_SUBCLIENT_TOKEN, db_user['auth'][0]['token'])
            self.assertEqual(str(BLENDER_ID_TEST_USERID), db_user['auth'][0]['user_id'])
            self.assertEqual('blender-id', db_user['auth'][0]['provider'])

            # Check that the token was succesfully stored.
            tokens = self.app.data.driver.db['tokens']
            db_token = tokens.find_one({'user': db_user['_id'],
                                        'token': scst})
            self.assertIsNotNone(db_token)

        return db_user