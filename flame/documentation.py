#! -*- coding: utf-8 -*-

# Description    Flame documentation class
#
# Authors:       Jose Carlos Gómez (josecarlos.gomez@upf.edu)
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
import pickle
import pandas as pd
import numpy as np

from flame.util import utils
from flame.conveyor import Conveyor
from flame.parameters import Parameters
from rdkit.Chem import AllChem
import hashlib



class Documentation:
    ''' Class storing the information needed to documentate models
        Fields are loaded from a YAML file (documentation.yaml)

        ...

        Attributes
        ----------

        fields : dict
            fields in the documentation
        version : int
            documentation version


        Methods
        -------

        load_parameters()
            Accesses to param file to retrieve all
            information needed to document the model.
        load_results()
            Accesses to build results to retrieve all
            information needed to document the model.
        assign_parameters()
            Fill documentation values corresponding to
             model parameter values
        assign_results()
            Assign result values to documentation fields
        get_upf_template()
            creates a spreedsheet QMRF-like
        get_prediction_template()
            Creates a reporting document for predictions
    
        '''

    def __init__(self, model, version=0, context='model'):
        ''' Load the fields from the documentation file'''

        self.model = model
        self.version = version
        self.fields = None
        self.parameters = Parameters()
        self.conveyor = None

        # obtain the path and the default name of the model documents
        documentation_file_path = utils.model_path(self.model, self.version)
        documentation_file_name = os.path.join(documentation_file_path,
                                               'documentation.yaml')

        # load the main class dictionary (p) from this yaml file
        if not os.path.isfile(documentation_file_name):
            raise Exception('Documentation file not found')

        try:
            with open(documentation_file_name, 'r') as documentation_file:
                self.fields = yaml.safe_load(documentation_file)
        except Exception as e:
            # LOG.error(f'Error loading documentation file with exception: {e}')
            raise e
        
        success, message = self.parameters.loadYaml(model, version)

        if not success:
            print(f'Parameters could not be loaded. {message}. Please make sure endpoint and version are correct')
            return
        
        # Remove this after acc
        #self.load_parameters()
        if context == 'model':
            self.load_results()
            self.assign_parameters()
            self.assign_results()
            self.setVal('md5',self.idataHash())


    def delta(self, model, version, doc, iformat='YAML', isSpace=False):
        ''' load a set of parameters from the configuration file present 
            at the model directory

            also, inserts the keys present in the param_file provided, 
            assuming that it contains a YAML-compatible format, like the one
            generated by manage

            adds some parameters identifying the model and the 
            hash of the configuration file 
        '''

        # if not self.loadYaml(model, version, isSpace):
        #     return False, 'file not found'
        
        # parse parameter file assuning it will be in
        # a YAML-compatible format
        if iformat == 'JSONS':
            try:
                newp = json.loads(doc)
            except Exception as e:
                return False, e
        else:
            try:
                with open(doc, 'r') as pfile:
                    if iformat == 'YAML':
                        newp = yaml.safe_load(pfile)
                    elif iformat == 'JSON':
                        newp = json.load(pfile)
            except Exception as e:
                return False, e
        
        # update interna dict with keys in the input file (delta)
        black_list = []
        for key in newp:
            if key not in black_list:
                val = newp[key]
                # YAML define null values as 'None, which are interpreted 
                # as strings
                if val == 'None':
                    val = None
                if isinstance(val, dict):
                    for inner_key in val:
                        inner_val = val[inner_key]
                        if inner_val == 'None':
                            inner_val = None
                        self.setInnerVal(key, inner_key, inner_val)
                        #print ('@delta: adding',key, inner_key, inner_val)
                else:
                    self.setVal(key, val)
                    #print ('@delta: adding',key,val,type(val))

        # dump internal dict to the parameters file
        if isSpace:
            parameters_file_path = utils.space_path(model, version)
        else: 
            parameters_file_path = utils.model_path(model, version)

        parameters_file_name = os.path.join (parameters_file_path,
                                            'documentation.yaml')
        try:
            with open(parameters_file_name, 'w') as pfile:
                yaml.dump (self.fields, pfile)
        except Exception as e:
            return False, 'unable to write parameters'
        
        self.setVal('md5',self.idataHash())

        return True, 'OK'

    def load_results(self):
        '''
            Load results pickle with model information
        '''
        # obtain the path and the default name of the results file
        results_file_path = utils.model_path(self.model, self.version)
        results_file_name = os.path.join(results_file_path,
                                         'model-results.pkl')
        self.conveyor = Conveyor()
        # load the main class dictionary (p) from this yaml file
        if not os.path.isfile(results_file_name):
            raise Exception('Results file not found')

        try:
            with open(results_file_name, "rb") as input_file:
                self.conveyor.load(input_file)
        except Exception as e:
            # LOG.error(f'No valid results pickle found at: 
            # {results_file_name}')
            raise e

    def getVal(self, key):
        ''' Return the value of the key parameter or None if it is
            not found in the parameters dictionary
        ''' 
        if not key in self.fields:
            return None

        if 'value' in self.fields[key]:
            return self.fields[key]['value']
        return None

    def getDict(self, key):
        ''' Return the value of the key parameter or None if it ises.
            not found in the parameters dictionary
        ''' 
        d = {}
        if not key in self.fields:
            return d

        element = self.fields[key]['value']
        if isinstance(element ,dict):
            # iterate keys and copy to the temp dictionary
            # the key and the content of 'value'
            for k, v in element.items():
                if 'value' in v:
                    d[k] = v['value']
        return d

    def setVal(self, key, value):
        ''' Sets the parameter defined by key to the given value
        '''
        # for existing keys, replace the contents of 'value'
        if key in self.fields:
            if "value" in self.fields[key]:
                if not isinstance(self.fields[key]['value'], dict):
                    self.fields[key]["value"] = value
                else:
                    # print(key)
                    for k in value.keys():
                        self.fields[key][k] = value[k]

        # for new keys, create a new element with 'value' key
        else:
            self.fields[key] = {'value': value}

    def setInnerVal(self, okey, ikey, value):
        ''' Sets a parameter within an internal dictionary. The entry is defined
            by a key of the outer dictionary (okey) and a second key in the inner
            dicctionary (ikey). The paramenter will be set to the given value

            This function test the existence of all the keys and dictionaries to 
            prevent crashes and returns without setting the value if any error is 
            found
        '''
        if not okey in self.fields:
            return

        if not "value" in self.fields[okey]:
            return

        odict = self.fields[okey]['value']

        if not isinstance(odict, dict):
            return
        
        if not ikey in odict:
            return
        if not isinstance(odict[ikey], dict):
            odict['value'] = value
            return
        if "value" in odict[ikey]:
            odict[ikey]["value"] = value
        else:
            odict[ikey] = {'value': value}

    def appVal(self, key, value):
        ''' Appends value to the end of existing key list 
        '''

        if not key in self.fields:
            return 

        if "value" in self.fields[key]:
            vt = self.fields[key]['value']

            # if the key is already a list, append the new value at the end
            if isinstance (vt, list):
                self.fields[key]['value'].append(value)
            # ... otherwyse, create a list with the previous content and the
            # new value
            else:
                self.fields[key]['value']=[vt, value]

    def dumpJSON (self):
        return json.dumps(self.fields, allow_nan=True)

    def assign_parameters(self):
        '''
            Fill documentation values corresponding to model parameter values
        '''

        if not self.parameters:
            raise ('Parameters were not loaded')

        # self.fields['Algorithm']['subfields']['algorithm']['value'] = \
        #     self.parameters.getVal('model')
        self.setInnerVal('Algorithm', 'algorithm', self.parameters.getVal('model'))
        
        if self.parameters.getVal('input_type')=='molecule':
            self.setInnerVal('Algorithm','descriptors', self.parameters.getVal('computeMD_method'))
        elif self.parameters.getVal('input_type')=='model_ensemble':
            self.setInnerVal('Algorithm','descriptors', 'ensemble models')

        if self.parameters.getVal('conformal'):
            self.setInnerVal('AD_method', 'name', 'conformal prediction')
            self.setVal('AD_parameters', f'Conformal Significance '
                     f'{self.parameters.getVal("conformalSignificance")}')


    def assign_results(self):
        '''
            Assign result values to documentation fields
        '''
        # Accepted validation keys
        allowed = ['Conformal_accuracy', 'Conformal_mean_interval',
                   'Conformal_coverage', 'Conformal_accuracy',
                   'Q2', 'SDEP', 
                   'SensitivityPred', 'SpecificityPred', 'MCCpred']
        gof_allowed = ['R2', 'SDEC', 'scoringR'
                       'Sensitivity', 'Specificity', 'MCC']
        model_info = self.conveyor.getVal('model_build_info')
        validation = self.conveyor.getVal('model_valid_info')


        # The code below to filter the hyperparameters to be 
        # reported.
        
        # Get parameter keys for the used estimator
        #param_key = self.parameters.getVal('model') + '_parameters'
        # Get parameter dictionary
        #estimator_params = self.parameters.getDict(param_key)
        
        self.fields['Algorithm_settings']['value'] = \
            (self.conveyor.getVal('estimator_parameters'))

        # Horrendous patch to solve backcompatibility problem
        if 'subfields' in self.fields['Data_info']:
            sub_label = 'subfields'
        else:
            sub_label = 'value'

        self.fields['Data_info']\
            [sub_label]['training_set_size']['value'] = \
            model_info[0][2]
        
        self.fields['Data_info']\
            [sub_label]['training_set_size']['value'] = \
            model_info[0][2]

        self.fields['Descriptors']\
            [sub_label]['final_number']['value'] = \
            model_info[1][2]
        self.fields['Descriptors']\
            [sub_label]['ratio']['value'] = \
            '{:0.2f}'.format(model_info[1][2]/model_info[0][2])
        
        internal_val = dict()
        for stat in validation:
            if stat[0] in allowed:
                internal_val[stat[0]] = float("{0:.2f}".format(stat[2]))
        if internal_val:
            self.fields['Internal_validation_1']\
                ['value'] = internal_val

        gof = dict()
        for stat in validation:
            if stat[0] in gof_allowed:
                gof[stat[0]] = float("{0:.2f}".format(stat[2]))
        if gof:
            self.fields['Goodness_of_fit_statistics']\
                ['value'] = gof


    def get_string(self, dictionary):
        '''
        Convert a dictionary (from documentation.yaml)
        to string format for the model template
        '''
        text = ''
        for key, val in dictionary.items():
            text += f'{key} : {val["value"]}\n'
        return text

    def get_string2(self, dictionary):
        '''
        Convert a dictionary (from parameter file) to 
        string format for the model template
        '''
        text = ''
        for key, val in dictionary.items():
            try:
                if isinstance(str(val), str):
                    text += f'{key} : {val}\n'
            except:
                continue

        return text

    def get_upf_template(self):
        '''
            This function creates a tabular model template based
            on the QMRF document type
        '''

        template = pd.DataFrame()
        template['ID'] = ['']
        template['Version'] = ['']
        template['Description'] = ['']
        template['Contact'] = ['']
        template['Institution'] = ['']
        template['Date'] = ['']
        template['Endpoint'] = ['']
        template['Endpoint_units'] = ['']
        template['Dependent_variable'] = ['']
        template['Species'] = ['']
        template['Limits_applicability'] = ['']
        template['Experimental_protocol'] = ['']
        template['Data_info'] = [self.get_string(
            self.fields['Data_info']['subfields'])]
        template['Model_availability'] = [\
            self.get_string(self.fields['Model_availability']
                            ['subfields'])]
        template['Algorithm'] = [self.get_string(
                                self.fields['Algorithm']['subfields']
                                )]
        template['Software'] = [self.get_string(
                                self.fields['Software']['subfields']
                                )]
        template['Descriptors'] = [self.get_string(
                                self.fields['Descriptors']['subfields']
                                )]
        template['Algorithm_settings'] = [self.get_string(
                        self.fields['Algorithm_settings']['subfields']
                        )]
        template['AD_method'] = [self.get_string(
                        self.fields['AD_method']['subfields']
                        )]
        template['AD_parameters'] = [self.fields['AD_parameters']['value']]
                        
        template['Goodness_of_fit_statistics'] = [self.fields\
                                ['Goodness_of_fit_statistics']['value']]
        template['Internal_validation_1'] = [self.fields[
                        'Internal_validation_1']['value']]
        template.to_csv('QMRF_template.tsv', sep='\t')

    def get_upf_template2(self):
        '''
            This function creates a tabular model template based
            on the QMRF document type
        '''
        fields = ['ID', 'Version', 'Contact', 'Institution',\
            'Date', 'Endpoint', 'Endpoint_units', 'Dependent_variable', 'Species',\
                'Limits_applicability', 'Experimental_protocol', 'Data_info',\
                    'Model_availability', 'Algorithm', 'Software', 'Descriptors',\
                        'Algorithm_settings', 'AD_method', 'AD_parameters',\
                            'Goodness_of_fit_statistics', 'Internal_validation_1' ]
        template = pd.DataFrame(columns=['Field', 'Parameter name', 'Parameter value'])
        for field in fields: 
            try:
                subfields = self.fields[field]['subfields']
            except:
                subfields = self.fields[field]['value']
            if subfields is not None:
                for index, subfield in enumerate(subfields):
                    field2 = ''
                    if index == 0:
                        field2 = field
                    else:
                        field2 = ""
                    value = str(subfields[subfield]['value'])
                    # None types are retrieved as str from yaml??
                    if value == "None":
                        value = ""
                    row = dict(zip(['Field', 'Parameter name', 'Parameter value'],\
                        [field2, subfield, value]))
                    template = template.append(row, ignore_index=True)
            else:
                value = str(self.fields[field]['value'])
                if value == 'None':
                    value = ""
                row = dict(zip(['Field', 'Parameter name', 'Parameter value'],\
                    [field, "", value]))
                template = template.append(row, ignore_index=True)
        template.to_csv('QMRF_template3.tsv', sep='\t', index=False)



    def get_prediction_template(self):
        '''
            This function creates a tabular model template based
            on the QMRF document type
        '''
        # obtain the path and the default name of the results file
        results_file_path = utils.model_path(self.model, self.version)
        results_file_name = os.path.join(results_file_path,
                                         'prediction-results.pkl')
        conveyor = Conveyor()
        # load the main class dictionary (p) from this yaml file
        if not os.path.isfile(results_file_name):
            raise Exception('Results file not found')
        try:
            with open(results_file_name, "rb") as input_file:
                conveyor.load(input_file)
        except Exception as e:
            # LOG.error(f'No valid results pickle found at: {results_file_name}')
            raise e        

        # First get Name, Inchi and InChIkey

        names = conveyor.getVal('obj_nam')
        smiles = conveyor.getVal('SMILES')
        inchi = [AllChem.MolToInchi(
                      AllChem.MolFromSmiles(m)) for m in smiles]
        inchikeys = [AllChem.InchiToInchiKey(
                     AllChem.MolToInchi(
                      AllChem.MolFromSmiles(m))) for m in smiles]
        predictions = []
        applicability = []
        if self.parameters['quantitative']['value']:
            raise('Prediction template for quantitative endpoints'
                  ' not implemented yet')
        if not self.parameters['conformal']['value']:
            predictions = conveyor.getVal('values')
        else:
            c0 = np.asarray(conveyor.getVal('c0'))
            c1 = np.asarray(conveyor.getVal('c1'))

            predictions = []
            for i, j in zip(c0, c1):
                prediction = ''
                if i == j:
                    prediction = 'out of AD'
                    applicability.append('out')
                if i != j:
                    if i == True:
                        prediction = 'Inactive'
                    else:
                        prediction = 'Active'
                    applicability.append('in')

                predictions.append(prediction)

        # Now create the spreedsheats for prediction

        # First write summary
        summary = ("Study name\n" +
                "Endpoint\n" +
                "QMRF-ID\n" +
                "(Target)Compounds\n" +
                "Compounds[compounds]\tName\tInChiKey\n")
        
        for name, inch in zip(names, inchikeys):
            summary += f'\t{name}\t{inch}\n'

        summary += ("\nFile\n" + 
                    "Author name\n" +
                    "E-mail\n" +
                    "Role\n" +
                    "Affiliation\n" +
                    "Date\n")
                
        with open('summary_document.tsv', 'w') as out:
            out.write(summary)

        # Now prediction details
        # Pandas is used to ease the table creation.

        reporting = pd.DataFrame()

        reporting['InChI'] = inchi
        reporting['CAS-RN'] = '-'
        reporting['SMILES'] = smiles
        reporting['prediction'] = predictions
        reporting['Applicability_domain'] = applicability
        reporting['reliability'] = '-'
        reporting['Structural_analogue_1_CAS'] = '-'
        reporting['Structural_analogue_1_smiles'] = '-'
        reporting['Structural_analogue_1_source'] = '-'
        reporting['Structural_analogue_1_experimental_value'] = '-'
        reporting['Structural_analogue_2_CAS'] = '-'
        reporting['Structural_analogue_2_smiles'] = '-'
        reporting['Structural_analogue_2_source'] = '-'
        reporting['Structural_analogue_2_experimental_value'] = '-'
        reporting['Structural_analogue_3_CAS'] = '-'
        reporting['Structural_analogue_3_smiles'] = '-'
        reporting['Structural_analogue_3_source'] = '-'
        reporting['Structural_analogue_3_experimental_value'] = '-'

        reporting.to_csv('prediction_report.tsv', sep='\t',index=False)

    def idataHash (self):
        ''' Create a md5 hash for a number of keys describing parameters
            relevant for idata

            This hash is compared between runs, to check wether idata must
            recompute or not the MD 
        '''

        # update with any new idata relevant parameter 
        keylist = ['SDFile_name','SDFile_activity','SDFile_experimental',
                   'normalize_method','ionize_method','convert3D_method',
                   'computeMD_method','TSV_varnames','TSV_objnames',
                   'TSV_activity','input_type']

        idata_params = []
        for i in keylist:
            idata_params.append(self.getVal(i))
        
        # MD_settings is a dictionary, obtain and sort the keys+values
        md_params = self.getDict('MD_settings')
        md_list = []
        for key in md_params:
            # combine key + value in a single string
            md_list.append(key+str(md_params[key]))

        idata_params.append(md_list.sort())

        # use picke as a buffered object, neccesary to generate the hexdigest
        p = pickle.dumps(idata_params)
        return hashlib.md5(p).hexdigest()
        


        
        

        
        

            




        
