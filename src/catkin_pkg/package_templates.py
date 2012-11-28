# Software License Agreement (BSD License)
#
# Copyright (c) 2008, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import print_function

import getpass
import os
import string
import sys

from catkin_pkg.package import Dependency
from catkin_pkg.package import Package
from catkin_pkg.package import PACKAGE_MANIFEST_FILENAME
from catkin_pkg.package import Person


class PackageTemplate(Package):

    def __init__(self, catkin_deps=None, **kwargs):
        super(PackageTemplate, self).__init__(**kwargs)
        self.catkin_deps = catkin_deps or []
        self.validate()

    @staticmethod
    def _create_package_template(package_name, description=None, licenses=None,
                                 maintainer_names=None, author_names=None,
                                 version=None, catkin_deps=None):
        """
        alternative factory method mapping CLI args to argument for
        Package class

        :param package_name:
        :param description:
        :param licenses:
        :param maintainer_names:
        :param authors:
        :param version:
        :param catkin_deps:
        """
        # Sort so they are alphebetical
        licenses = list(licenses or ["TODO"])
        licenses.sort()
        if not maintainer_names:
            maintainer_names = [getpass.getuser()]
        maintainer_names = list(maintainer_names or [])
        maintainer_names.sort()
        maintainers = []
        for maintainer_name in maintainer_names:
            maintainers.append(
                Person(maintainer_name,
                       '%s@todo.todo' % maintainer_name.split()[-1])
            )
        author_names = list(author_names or [])
        author_names.sort()
        authors = []
        for author_name in author_names:
            authors.append(Person(author_name))
        catkin_deps = list(catkin_deps or [])
        catkin_deps.sort()
        pkg_catkin_deps = []
        for dep in catkin_deps:
            if dep.lower() == 'catkin':
                catkin_deps.remove(dep)
                continue
            pkg_catkin_deps.append(Dependency(dep))
        package_temp = PackageTemplate(
            name=package_name,
            version=version or '0.0.0',
            description=description or 'The %s package' % package_name,
            build_depends=pkg_catkin_deps,
            buildtool_depends=[Dependency('catkin')],
            catkin_deps=catkin_deps,
            licenses=licenses,
            authors=authors,
            maintainers=maintainers,
            urls=[])
        return package_temp


def read_template_file(filename, rosdistro):
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    template = os.path.join(template_dir, rosdistro, '%s.in' % filename)
    if not os.path.isfile(template):
        raise IOError(
            "Could not read template for ROS distro "
            "'{}' at '{}': ".format(rosdistro, template) +
            "no such file or directory"
        )
    with open(template, 'r') as fhand:
        template_contents = fhand.read()
    return template_contents


def _safe_write_files(newfiles, target_dir):
    """
    writes file contents to target_dir/filepath for all entries of newfiles.
    Aborts early if files exist in places for new files or directories

    :param newfiles: a dict {filepath: contents}
    :param target_dir: a string
    """
    # first check no filename conflict exists
    for filename in newfiles:
        target_file = os.path.join(target_dir, filename)
        if os.path.exists(target_file):
            raise ValueError('File exists: %s' % target_file)
        dirname = os.path.dirname(target_file)
        while(dirname != target_dir):
            if os.path.isfile(dirname):
                raise ValueError('Cannot create directory, file exists: %s' %
                                 dirname)
            dirname = os.path.dirname(dirname)

    for filename, content in newfiles.items():
        target_file = os.path.join(target_dir, filename)
        dirname = os.path.dirname(target_file)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        # print(target_file, content)
        with open(target_file, 'ab') as fhand:
            fhand.write(content)


def create_package_files(target_path, package_template, rosdistro='groovy',
                         newfiles=None):
    """
    creates several files from templates to start a new package.

    :param target_path: parent folder where to create the package
    :param package_template: contains the required information
    :param rosdistro: name of the distro to look up respective template
    :param newfiles: dict {filepath: contents} for additional files to write
    """
    if newfiles is None:
        newfiles = {}
    # allow to replace default templates when path string is equal
    manifest_path = os.path.join(target_path, PACKAGE_MANIFEST_FILENAME)
    if manifest_path not in newfiles:
        newfiles[manifest_path] = \
            create_package_xml(package_template, rosdistro)
    cmake_path = os.path.join(target_path, 'CMakeLists.txt')
    if not cmake_path in newfiles:
        newfiles[cmake_path] = create_cmakelists(package_template, rosdistro)
    _safe_write_files(newfiles, target_path)


class CatkinTemplate(string.Template):
    """subclass to use @ instead of $ as markers"""
    delimiter = '@'
    escape = '@'


def create_cmakelists(package_template, rosdistro):
    """
    :param package_template: contains the required information
    :returns: file contents as string
    """
    cmakelists_txt_template = read_template_file('CMakeLists.txt', rosdistro)
    ctemp = CatkinTemplate(cmakelists_txt_template)
    if package_template.catkin_deps == []:
        components = ''
    else:
        components = ' COMPONENTS %s' % ' '.join(package_template.catkin_deps)
    temp_dict = {'name': package_template.name,
                 'components': components}
    return ctemp.substitute(temp_dict)


def _create_depend_tag(dep_type,
                       name,
                       version_eq=None,
                       version_lt=None,
                       version_lte=None,
                       version_gt=None,
                       version_gte=None):
    """
    Helper to create xml snippet for package.xml
    """

    version_string = []
    for key, var in {'version_eq': version_eq,
                     'version_lt': version_lt,
                     'version_lte': version_lte,
                     'version_gt': version_gt,
                     'version_gte': version_gte}.items():
        if var is not None:
            version_string.append(' %s="%s"' % (key, var))
    result = '  <%s%s>%s</%s>\n' % (dep_type,
                                  ''.join(version_string),
                                  name,
                                  dep_type)
    return result


def create_package_xml(package_template, rosdistro):
    """
    :param package_template: contains the required information
    :returns: file contents as string
    """
    package_xml_template = \
        read_template_file(PACKAGE_MANIFEST_FILENAME, rosdistro)
    ctemp = CatkinTemplate(package_xml_template)
    temp_dict = {}
    for key in package_template.__slots__:
        temp_dict[key] = getattr(package_template, key)

    if package_template.version_abi:
        temp_dict['version_abi'] = ' abi="%s"' % package_template.version_abi
    else:
        temp_dict['version_abi'] = ''

    if not package_template.description:
        temp_dict['description'] = 'The %s package ...' % package_template.name

    licenses = []
    for plicense in package_template.licenses:
        licenses.append('  <license>%s</license>\n' % plicense)
    temp_dict['licenses'] = ''.join(licenses)

    def get_person_tag(tagname, person):
        email_string = (
            "" if person.email is None else 'email="%s"' % person.email
        )
        return '  <%s %s>%s</%s>\n' % (tagname, email_string,
                                       person.name, tagname)

    maintainers = []
    for maintainer in package_template.maintainers:
        maintainers.append(get_person_tag('maintainer', maintainer))
    temp_dict['maintainers'] = ''.join(maintainers)

    urls = []
    for url in package_template.urls:
        type_string = ("" if url.type is None
                       else 'type="%s"' % url.type)
        urls.append('    <url %s >%s</url>\n' % (type_string, url.url))
    temp_dict['urls'] = ''.join(urls)

    authors = []
    for author in package_template.authors:
        authors.append(get_person_tag('author', author))
    temp_dict['authors'] = ''.join(authors)

    dependencies = []
    dep_map = {
        'build_depend': package_template.build_depends,
        'buildtool_depend': package_template.buildtool_depends,
        'run_depend': package_template.run_depends,
        'test_depend': package_template.test_depends,
        'conflict': package_template.conflicts,
        'replace': package_template.replaces
    }
    for dep_type in ['buildtool_depend', 'build_depend', 'run_depend',
                     'test_depend', 'conflict', 'replace']:
        for dep in sorted(dep_map[dep_type], key=lambda x: x.name):
            if 'depend' in dep_type:
                dep_tag = _create_depend_tag(
                    dep_type,
                    dep.name,
                    dep.version_eq,
                    dep.version_lt,
                    dep.version_lte,
                    dep.version_gt,
                    dep.version_gte
                    )
                dependencies.append(dep_tag)
            else:
                dependencies.append(_create_depend_tag(dep_type,
                                                       dep.name))
    temp_dict['dependencies'] = ''.join(dependencies)

    exports = []
    if package_template.exports is not None:
        for export in package_template.exports:
            if export.content is not None:
                print('WARNING: Create package does not know how to '
                      'serialize exports with content: '
                      '%s, %s, ' % (export.tagname, export.attributes) +
                      '%s' % (export.content),
                      file=sys.stderr)
            else:
                attribs = ['%s="%s"' % (k, v) for (k, v) in export.attributes]
                line = '    <%s%s/>\n' % (export.tagname, ''.join(attribs))
                exports.append(line)
    temp_dict['exports'] = ''.join(exports)

    temp_dict['components'] = package_template.catkin_deps

    return ctemp.substitute(temp_dict)
