# Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import functools
import re

import subunit
import testtools

DAY_SECONDS = 60 * 60 * 24


def get_duration(start, end):
    if not start or not end:
        duration = None
    else:
        delta = end - start
        duration = '%d.%06d' % (
            delta.days * DAY_SECONDS + delta.seconds, delta.microseconds)
        return float(duration)


class ReadSubunit(object):

    def __init__(self, stream_file, attachments=False, attr_regex=None):
        self.stream_file = stream_file
        self.stream = subunit.ByteStreamToStreamResult(stream_file)
        starts = testtools.StreamResult()
        summary = testtools.StreamSummary()
        outcomes = testtools.StreamToDict(functools.partial(
            self.parse_outcome))
        self.result = testtools.CopyStreamResult([starts, outcomes, summary])
        self.results = {}
        self.attachments = attachments
        if attr_regex:
            self.attr_regex = re.compile(attr_regex)
        # NOTE(mtreinish): Default to the previous implicit regex if None is
        # specified for backwards compat
        else:
            self.attr_regex = re.compile('\[(.*)\]')

    def get_results(self):
        self.result.startTestRun()
        try:
            self.stream.run(self.result)
        finally:
            self.result.stopTestRun()
        self.results['run_time'] = self.run_time()
        return self.results

    def get_attachments(self, test):
        attach_dict = {}
        for name, detail in test['details'].items():
            name = name.split(':')[0]
            attach_dict[name] = detail
        return attach_dict

    def parse_outcome(self, test):
        metadata = {}
        status = test['status']
        if status == 'exists':
            return
        name = self.cleanup_test_name(test['id'])
        attrs = self.get_attrs(test['id'])
        if attrs:
            metadata['attrs'] = attrs
        if test['tags']:
            metadata['tags'] = ",".join(test['tags'])
        # Return code is a fail don't process it
        if name == 'process-returncode':
            return
        timestamps = test['timestamps']
        attachment_dict = {}
        if self.attachments:
            attachment_dict = self.get_attachments(test)
        self.results[name] = {
            'status': status,
            'start_time': timestamps[0],
            'end_time': timestamps[1],
            'metadata': metadata,
            'attachments': attachment_dict
        }
        self.stream_file.flush()

    def get_attrs(self, name):
        matches = self.attr_regex.search(name)
        if matches:
            attrs = matches.group(1)
        else:
            attrs = None
        return attrs

    def cleanup_test_name(self, name, strip_tags=True, strip_scenarios=False):
        """Clean up the test name for display.

        By default we strip out the tags in the test because they don't help us
        in identifying the test that is run to it's result.

        Make it possible to strip out the testscenarios information (not to
        be confused with tempest scenarios) however that's often needed to
        identify generated negative tests.
        """
        if strip_tags:
            matches = self.attr_regex.search(name)
            if matches:
                tags_start = matches.start(0)
                tags_end = matches.end(0)
                if tags_start > 0 and tags_end > tags_start:
                    newname = name[:tags_start]
                    newname += name[tags_end:]
                    name = newname

        if strip_scenarios:
            tags_start = name.find('(')
            tags_end = name.find(')')
            if tags_start > 0 and tags_end > tags_start:
                newname = name[:tags_start]
                newname += name[tags_end + 1:]
                name = newname
        return name

    def run_time(self):
        runtime = 0.0
        for name, data in self.results.items():
            runtime += get_duration(data['start_time'], data['end_time'])
        return runtime
