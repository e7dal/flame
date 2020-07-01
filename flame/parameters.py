#! -*- coding: utf-8 -*-

# Description    Flame Build class
#
# Authors:       Manuel Pastor (manuel.pastor@upf.edu)
#
# Copyright 2018 Manuel Pastor
#
# This file is part of Flame
#
# Flame is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation version 3.
#
# Flame is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Flame. If not, see <http://www.gnu.org/licenses/>.

import os
import yaml
import json
import hashlib
import pickle

from flame.util import utils


class Parameters:
    ''' Class storing a large set of parameters defining how a model is built

        These parameters are loaded from a configuration file (typically 
        in yaml format) 

        The version 1 of parameters.yaml is a simple "key-value" python dictionary
        in yaml file

        In version 2 every parameter is a dictionary with keys defining the parameter type, 
        value and providing a human-readable explanation used for the GUI

        This code supports both versions of the parameter file, but the use of version 1
        is deprecated and will not be supported indefinitely 
    '''

    def __init__(self):
        ''' constructor '''
        self.extended = False
        self.param_format = 1
        return

    # def loadDict (self, d):
    #     ''' load the content from a dictionary '''
    #     self.p = d    
    #     return

    def loadYaml(self, model, version, isSpace=False):       
        ''' load a set of parameters from the configuration file present 
            at the model directory

            adds some parameters identifying the model and the 
            hash of the configuration file 
        '''

        # obtain the path and the default name of the model parameters
        if isSpace:
            parameters_file_path = utils.space_path(model, version)
        else:
            parameters_file_path = utils.model_path(model, version)
        
        if not os.path.isdir (parameters_file_path):
            return False, f'Model "{model}", version "{version}" not found'

        parameters_file_name = os.path.join (parameters_file_path,
                                            'parameters.yaml')

        # load the main class dictionary (p) from this yaml file
        if not os.path.isfile(parameters_file_name):
            return False, 'Parameters file not found'

        try:
            with open(parameters_file_name, 'r') as pfile:
                self.p = yaml.safe_load(pfile)
        except Exception as e:
            return False, e

        # check version of the parameter file
        # no 'version' key mans version < 2.0
        if 'param_format' in self.p:
            self.extended = True
        else:
            self.extended = False
            self.param_format = 1.0

        # # correct CV to kfold for conformal models
        # if self.getVal('conformal') is True:
        #     self.setVal('ModelValidationCV','kfold')
        if self.getVal('model') == 'majority':
            self.setVal('conformal',False)

        # add keys for the model and a MD5 hash
        self.setVal('endpoint',model)
        self.setVal('version',version)
        self.setVal('model_path',parameters_file_path)
        # self.setVal('md5',utils.md5sum(parameters_file_name))
        self.setVal('md5',self.idataHash())

        return True, 'OK'

    def delta(self, model, version, param, iformat='YAML', isSpace=False):
        ''' load a set of parameters from the configuration file present 
            at the model directory

            also, inserts the keys present in the param_file provided, 
            assuming that it contains a YAML-compatible format, like the one
            generated by manage

            adds some parameters identifying the model and the 
            hash of the configuration file 
        '''

        if not self.loadYaml (model, version, isSpace):
            return False, 'file not found'
        
        # parse parameter file assuning it will be in
        # a YAML-compatible format
        if iformat == 'JSONS':
            try:
                newp = json.loads(param)
            except Exception as e:
                return False, e
        else:
            try:
                with open(param, 'r') as pfile:
                    if iformat == 'YAML':
                        newp = yaml.safe_load(pfile)
                    elif iformat == 'JSON':
                        newp = json.load(pfile)
            except Exception as e:
                return False, e
        
        # update interna dict with keys in the input file (delta)
        black_list = ['param_format','version','model_path','endpoint','md5']
        for key in newp:
            if key not in black_list:

                val = newp[key]

                # YAML define null values as 'None, which are interpreted 
                # as strings
                if val == 'None':
                    val = None

                if isinstance(val ,dict):
                    for inner_key in val:
                        inner_val = val[inner_key]

                        if inner_val == 'None':
                            inner_val = None

                        self.setInnerVal(key, inner_key, inner_val)
                        #print ('@delta: adding',key, inner_key, inner_val)
                else:
                    self.setVal(key,val)
                    #print ('@delta: adding',key,val,type(val))

        # dump internal dict to the parameters file
        if isSpace:
            parameters_file_path = utils.space_path(model, version)
        else: 
            parameters_file_path = utils.model_path(model, version)

        parameters_file_name = os.path.join (parameters_file_path,
                                            'parameters.yaml')
        try:
            with open(parameters_file_name, 'w') as pfile:
                yaml.dump (self.p, pfile)
        except Exception as e:
            return False, 'unable to write parameters'

        # # correct CV to kfold for conformal models
        # if self.getVal('conformal') is True:
        #     self.setVal('ModelValidationCV','kfold')
        if self.getVal('model') == 'majority':
            self.setVal('conformal',False)

        # self.setVal('md5',utils.md5sum(parameters_file_name))
        self.setVal('md5',self.idataHash())

        return True, 'OK'

    @staticmethod
    def saveJSON(self, model, version, input_JSON):
        p = json.load(input_JSON)
        parameters_file_path = utils.model_path(model, version)
        parameters_file_name = os.path.join (parameters_file_path,
                                            'parameters.yaml')
        try:
            with open(parameters_file_name, 'w') as pfile:
                yaml.dump (p, pfile)
        except Exception as e:
            return False

        return True

    def update_file(self, model, version=0):
        '''Function to save current parameter values modified
        at the object level (i.e: From a interactive python shell)
        '''
        p = self.p
        if not p:
            return False, 'No loaded parameters'

        parameters_file_path = utils.model_path(model, version)
        parameters_file_name = os.path.join (parameters_file_path,
                                            'parameters.yaml')
        try:
            with open(parameters_file_name, 'w') as pfile:
                yaml.dump (p, pfile)
        except Exception as e:
            return False, e
        return True

    def getVal(self, key):
        ''' Return the value of the key parameter or None if it is
            not found in the parameters dictionary
        ''' 
        if not key in self.p:

            ## legacy models use conformalSignificance instead
            ## of confidence
            if key == 'conformalConfidence':
                temp = self.getVal('conformalSignificance')
                if temp is None:
                    return None
                else:
                    return 1.0 - temp
            return None

        ## compatibility with version 1 (remove)
        if not self.extended:
            return self.p[key]
        ## ---------------------------------------


        if 'value' in self.p[key]:
            return self.p[key]['value']
        return None

    
    def getDict(self, key):
        ''' Return the value of the key parameter or None if it ises.
            not found in the parameters dictionary
        ''' 
        d = {}
        if not key in self.p:
            return d

        ## compatibility with version 1 (remove)
        if not self.extended:
            return self.p[key]
        ## ---------------------------------------

        element = self.p[key]['value']
        if isinstance(element ,dict):
            # iterate keys and copy to the temp dictionary
            # the key and the content of 'value'
            for k, v in element.items():
                if 'value' in v:
                    d[k] = v['value']
        return d

    
    # def getOldParam(self):
    #     ''' Returns the dictionary with the parameters
    #         This function was defined only for compatibility purposes
    #         during the implementation of this class
    #     '''
    #     return self.p

    def setVal(self, key, value):
        ''' Sets the parameter defined by key to the given value
        '''

        # compatibility with version 1 (remove)
        if not self.extended:
            self.p[key] = value
            return

        # for existing keys, replace the contents of 'value'
        if key in self.p:
            if "value" in self.p[key]:
                if not isinstance(self.p[key]['value'], dict):
                    self.p[key]["value"] = value
                else:
                    for k in value.keys():
                        self.p[key][k] = value[k]

        # for new keys, create a new element with 'value' key
        else:
            self.p[key] = {'value': value}

    def setInnerVal(self, okey, ikey, value):
        ''' Sets a parameter within an internal dictionary. The entry is defined
            by a key of the outer dictionary (okey) and a second key in the inner
            dicctionary (ikey). The paramenter will be set to the given value

            This function test the existence of all the keys and dictionaries to 
            prevent crashes and returns without setting the value if any error is 
            found
        '''

        if not okey in self.p:
            return

        if not "value" in self.p[okey]:
            return

        odict = self.p[okey]['value']

        if not isinstance(odict, dict):
            return
        
        if not ikey in odict:
            return

        if "value" in odict[ikey]:
            odict[ikey]["value"] = value
        else:
            odict[ikey] = {'value': value}


    def appVal(self, key, value):
        ''' Appends value to the end of existing key list 
        '''

        if not key in self.p:
            return 

        ## compatibility with version 1 (remove)
        if not self.extended:
            self.p[key].append(value)
            return
        ## ---------------------------------------

        if "value" in self.p[key]:
            vt = self.p[key]['value']

            # if the key is already a list, append the new value at the end
            if isinstance (vt, list):
                self.p[key]['value'].append(value)
            # ... otherwyse, create a list with the previous content and the
            # new value
            else:
                self.p[key]['value']=[vt, value]

    def getEnsemble (self):
        ''' Returns a Boolean indicating if the model uses external input
            sources and a list with the name of these endpoints 
        '''
        ext_input = False
        ensemble_names = None
        ensemble_versions = None

        ensemble_names = self.getVal('ensemble_names')
        ensemble_versions = self.getVal('ensemble_versions')


        if ensemble_names is not None: 
            nnames = len (ensemble_names)
            if nnames > 0:
                ext_input = True
        
                if ensemble_versions == None or len(ensemble_versions)!= nnames:
                    ensemble_versions = [0 for i in range (nnames)]

        return (ext_input, ensemble_names, ensemble_versions)

    def dumpJSON (self):
        return json.dumps(self.p)

    def idataHash (self):
        ''' Create a md5 hash for a number of keys describing parameters
            relevant for idata

            This hash is compared between runs, to check wether idata must
            recompute or not the MD 
        '''

        # update with any new idata relevant parameter 
        keylist = ['model_path','version','SDFile_name','SDFile_activity','SDFile_experimental',
                   'normalize_method','ionize_method','convert3D_method',
                   'computeMD_method','TSV_varnames','TSV_objnames',
                   'TSV_activity','input_type','endpoint']

        idata_params = []
        for i in keylist:
            idata_params.append(self.getVal(i))
        
        # MD_settings is a dictionary, obtain and sort the keys+values
        md_params = self.getDict('MD_settings')
        md_list = []
        for key in md_params:
            # combine key + value in a single string
            md_list.append(key+str(md_params[key]))
        md_list.sort()
        idata_params.append(md_list)

        # use picke as a buffered object, neccesary to generate the hexdigest
        p = pickle.dumps(idata_params)
        return hashlib.md5(p).hexdigest()