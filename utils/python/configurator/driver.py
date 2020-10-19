try:
    import configparser as par
    from configparser import NoOptionError, NoSectionError

except ImportError:
    import ConfigParser as par
    from ConfigParser import NoOptionError, NoSectionError




import os
import os.path as p
import subprocess as sub
import time

from future.utils import iteritems

from utils import working_directory


def configurate(build_dir=".", data_path="../input/data.conf", **options):
    """Main function for configuring MITgcm simulations."""

    data_file = p.join(build_dir, data_path)
    data, data_sections, data_section_map = default_data()
    data.read(data_file)
    merge_config(data, options, data_section_map)

    with working_directory(build_dir):
        # XXX Try to avoid overwriting the input configuration
        with open('data-merged.conf', 'w') as f:
            data.write(f)
        generate_parameters_file(data, data_sections, data_section_map)


def default_data():
    """Configuration defaults before parsing input files.

    The configuration is represented as a ConfigParser.RawConfigParser instance."""
    sections = ["PARM01", "PARM02", "PARM03", "PARM04", "PARM05",]

    section_map = {
        "viscAh"              : "PARM01",
        "f0"                  : "PARM01",
        "beta"                : "PARM01",
        "rhoConst"            : "PARM01",
        "gBaro"               : "PARM01",
        "rigidLid"            : "PARM01",
        "implicitFreeSurface" : "PARM01",
        "momAdvection"        : "PARM01",
        "tempStepping"        : "PARM01",
        "saltStepping"        : "PARM01",
    }


    data = par.RawConfigParser()
    for section in sections:
        data.add_section(section)
    data.set("PARM01", "gravity",           "9.81")
    data.set("PARM01", "rigidLid",          "False")
    data.set("PARM01", "implicitFreeSurface", "False")
    data.set("PARM01", "momAdvection",      "False")
    data.set("PARM01", "tempStepping",      "False")
    data.set("PARM01", "saltStepping",      "False")

    data.optionxform = str
    return data, sections, section_map


def merge_config(data, options, data_section_map):
    """Merge the options given in the `options` dict into the RawConfigParser instance `data`.

    Mutates the given data instance."""
    for k, v in iteritems(options):
        if k in data_section_map:
            section = data_section_map[k]
            if not data.has_section(section):
                data.add_section(section)
            if v == True: v = "yes"
            if v == False: v = "no"
            data.set(section, k, v)
        else:
            raise Exception("Unrecognized option", k)

def fortran_option_string(section, name, config):
    """Convert option values to strings that Fortran namelists will understand correctly.

    Two conversions are of interest: Booleans are rendered as
    .TRUE. or .FALSE., and options that are input fields are rendered
    as the file names where `generate_input_data_files` has written
    those data, or the Fortran empty string `''` if no file is written
    (which means the core should use its internal default).
    """

    if name in ["rigidLid", "implicitFreeSurface", "momAdvection",
                "tempStepping", "saltStepping"]:
        # Avoid needing to set all Boolean variables in data.conf
        try:
            if config.getboolean(section, name):
                return ".TRUE."
            else:
                return ".FALSE."
        except NoOptionError as e:
            pass
    else:
        if config.has_option(section, name):
            return config.get(section, name)
        else:
            return None

def generate_parameters_file(data, data_sections, data_section_map):
    with open('data', 'w') as f:
        for section in data.sections():
            if section not in data_sections:
                raise Exception("Detected unexpected section name %s", section)
            f.write(' &')
            f.write(section.upper())
            f.write('\n')
            for (name, section1) in iteritems(data_section_map):
                if section1 != section: continue
                val = fortran_option_string(section, name, data)
                if val is not None:
                    f.write(' %s = %s,\n' % (name, val))
            f.write(' /\n')