# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Self-contained finite grammar cases, no runtime CLI or evidence file reads."""
import unittest
from tools.agent_memory_runtime.query_validation_field_request import validation_field_request as request, validation_field_matches as matches, RESERVED
FROZEN=[('Locate the display name validation-stop and dispatch source.', 'field:display_name'), ('请定位客户编号校验中止和动作分发源码。', 'field:customer_code'), ('A required account field shows an error but the invalid update still submits. Locate the validation-stop and dispatch owner.', 'domain:account'), ('A required purchase field shows an error but the invalid update still submits. Locate the validation-stop and dispatch owner.', 'domain:purchase'), ('必填显示名为空时提示错误但仍提交更新，请定位校验中止和动作分发源码。', 'field:display_name'), ('必填客户编号为空时提示错误但仍提交更新，请定位校验中止和动作分发源码。', 'field:customer_code'), ('Locate the validation-stop and dispatch source.', None), ('Locate PurchaseEntry.submitPurchase implementation.', None), ('Find the literal text "display name validation-stop and dispatch source".', None), ('Do not return the display name validation-stop and dispatch source.', None), ('Return display name validation and customer code validation sources.', None), ('Trace the call path from ProfileEntry.submitProfile to dispatchProfile.', None), ('A required purchase field shows an error but the invalid update still submits. Locate the account validation-stop and dispatch source.', None), ('Locate the display name validation-stop and dispatch source. Return the logger.', None), ('Locate the current validation-stop and dispatch source.', None), ('Locate the display name validation-stop and dispatch source.', 'field:display_name'), ('必填显示名为空时提示错误但仍提交更新，请定位校验中止和动作分发源码。', 'field:display_name'), ('Locate the account validation-stop and dispatch source.', 'domain:account'), ('A required account field shows an error but the invalid update still submits. Locate the validation-stop and dispatch owner.', 'domain:account'), ('Locate the display name validation-stop and dispatch source.', 'field:display_name'), ('Locate the customer code validation-stop and dispatch source.', 'field:customer_code'), ('必填显示名为空时提示错误但仍提交更新，请定位校验中止和动作分发源码。', 'field:display_name'), ('Return the display name validation source and the error logger.', None), ('Locate the display name validation-stop and dispatch source.', 'field:display_name')]

class ValidationFieldRequestTests(unittest.TestCase):
    def test_all_frozen_inputs(self):
        for q,wanted in FROZEN:
            if wanted is None:self.assertIsNone(request(q),q);continue
            kind,value=wanted.split(':');expected=tuple(value.split('_'))if kind=='field'else value
            self.assertEqual(request(q),dict(kind=kind,value=expected),q)
    def test_five_families_and_two_domains(self):
        for field,zh,parts in [('display name','显示名',('display','name')),('customer code','客户编号',('customer','code'))]:
            for q in (f'Locate the {field} validation-stop and dispatch source.',f'请定位{zh}校验中止和动作分发源码。',f'必填{zh}为空时提示错误但仍提交更新，请定位校验中止和动作分发源码。'):
                self.assertEqual(request(q),dict(kind='field',value=parts))
        for domain in ('account','purchase','roster'):
            for q in (f'Locate the {domain} validation-stop and dispatch source.',f'A required {domain} field shows an error but the invalid update still submits. Locate the validation-stop and dispatch owner.'):
                self.assertEqual(request(q),dict(kind='domain',value=domain))
    def test_case_punctuation_whitespace_and_type_are_exact(self):
        q=FROZEN[0][0]
        for bad in (None,True,42,'',q.lower(),q.upper(),' '+q,q+' ',q[:-1],q+'\n',q.replace('Locate','Locate\n'),q.replace('the ','the  '),q.replace('display name','Display Name'),q.replace('display name','display_name'),q.replace('.','。')):
            self.assertIsNone(request(bad),repr(bad))
    def test_reserved_domain_and_length(self):
        for word in RESERVED:self.assertIsNone(request(f'Locate the {word} validation-stop and dispatch source.'),word)
        self.assertIsNotNone(request('Locate the '+'z'*24+' validation-stop and dispatch source.'))
        self.assertIsNone(request('Locate the '+'z'*25+' validation-stop and dispatch source.'))
        self.assertIsNone(request('x'*241))
        for word in ('account2','two_words','Account','客户','account-purchase'):
            self.assertIsNone(request(f'Locate the {word} validation-stop and dispatch source.'))
    def test_negation_quotes_suffix_conflict_and_page_are_unsupported(self):
        q=FROZEN[0][0]
        for bad in ('"'+q+'"','`'+q+'`','not '+q,q+' or customer code',q+' Return Logger.',q.replace('display name','not display name'),q.replace('display name','display name or customer code'),q.replace('dispatch','dispatch except save'),'An empty display name causes an account validation error; return the guarded page action.','必填显示名为空时提示错误但仍提交更新，请定位客户编号校验中止和动作分发源码。'):
            self.assertIsNone(request(bad),bad)
    def test_field_complete_identifier_part_sequence(self):
        permission=request(FROZEN[0][0])
        for field in ('displayName','DisplayName','display_name','DISPLAY_NAME'):
            self.assertTrue(matches(permission,'Anything','submit',field),field)
        for field in ('oldDisplayName','displayNameOld','displayNames','displayname','customerCode','display.name','displayName[0]','',None):
            self.assertFalse(matches(permission,'Anything','submit',field),repr(field))
    def test_domain_same_owner_or_same_method_whole_part(self):
        p=request('Locate the account validation-stop and dispatch source.')
        for owner,method in (('AccountEditor','submit'),('Other','submitAccount'),('account','run'),('Other','account')):
            self.assertTrue(matches(p,owner,method,'customerCode'))
        for owner,method in (('AccountingEditor','submit'),('Other','submitAccounting'),('Other','dispatch'),('Discount','run')):
            self.assertFalse(matches(p,owner,method,'account'))
        self.assertFalse(matches(p,'Other','run','account'))
    def test_unknown_permissions_and_bad_identifiers(self):
        for p in (None,{},dict(kind='field',value=['display','name']),dict(kind='domain',value='current'),dict(kind='domain',value='Account'),dict(kind='field',value=('old','display','name')),dict(kind='field',value=('display','name'),extra=True)):
            self.assertFalse(matches(p,'AccountEditor','submit','displayName'))
        p=request(FROZEN[0][0])
        for owner,method in (('A.B','submit'),('A','run()'),('', 'run'),(None,'run')):
            self.assertFalse(matches(p,owner,method,'displayName'))
    def test_original_three_request_bytes_only(self):
        self.assertEqual(request('A required account field shows an error but the invalid update still submits. Locate the validation-stop and dispatch owner.'),dict(kind='domain',value='account'))
        self.assertIsNone(request('An empty display name reports an error yet submits the account update; return the guarded page action.'))
        self.assertEqual(request('必填显示名为空时提示错误但仍提交更新，请定位校验中止和动作分发源码。'),dict(kind='field',value=('display','name')))
