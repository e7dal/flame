#! -*- coding: utf-8 -*-

##    Description    Flame Learn class
##
##    Authors:       Manuel Pastor (manuel.pastor@upf.edu)
##
##    Copyright 2018 Manuel Pastor
##
##    This file is part of Flame
##
##    Flame is free software: you can redistribute it and/or modify
##    it under the terms of the GNU General Public License as published by
##    the Free Software Foundation version 3.
##
##    Flame is distributed in the hope that it will be useful,
##    but WITHOUT ANY WARRANTY; without even the implied warranty of
##    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##    GNU General Public License for more details.
##
##    You should have received a copy of the GNU General Public License
##    along with Flame.  If not, see <http://www.gnu.org/licenses/>.

from RF import RF
import numpy as np

class Learn:

    def __init__ (self, control, results):

        self.control = control # control object defining the processing
        self.results = results # results is a tuple with X, Y and ... (to be defined)
        self.vpath = './'

    def getMatrices (self):
        """ 
        
        Returns NumPy X and Y matrices extracted from results
        
        """
        
        ncol = 0
        xx = []
        yy = []

        # obtain X and Y from tuple elements 0 (MD) and 1 (Activity)
        for i in self.results:
            if len(i[0])>ncol: ncol = len(i[0])
            xx.append(i[0])
            yy.append(i[1])

        nrow = len (xx)

        Y = np.array (yy,dtype=np.float64)
        X = np.empty ((nrow,ncol),dtype=np.float64)

        i=0
        for row in xx:
            X[i,:]=np.array(row,dtype=np.float64)
            i+=1

        return X, Y

    def runRF (self):

        print ('hi! I am Random Forest')

        return True, 'debug RF results'

    def run (self):
        X,Y = self.getMatrices ()

        nobj, nvarx = np.shape(X)

        if (nobj==0) or (nvarx==0) :
            return False, 'failed to extract activity or to generate MD'

        nobj = np.shape(Y)
        if (nobj==0) :
            return False, 'no activity found'
        
        model = ''
        
        # initilizate estimator
       
        if self.control.model == 'RF':
            model = RF(X,Y, quantitative, modelAutoscaling, tune,
                        ModelValidationCV, ModelValidationN, ModelValidationP, ModelValidationLC,
                        conformalSignificance, vpath, RF_parameters, RF_optimize, conformal)
        else:
            return False, 'modeling method not recognised'
            
        # build model
        
        model.build()

        # validate model
        
        model.validate()
            
        # save model

        with open(self.vpath +  model.name + '.pickle', 'wb') as handle:
            pickle.dump(model , handle, protocol=pickle.HIGHEST_PROTOCOL)
        
        # compute AD (when applicable)

        success = True
        results = 'debug learn.run results'

        return success, results

