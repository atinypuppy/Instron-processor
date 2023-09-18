#####################################################
###   Code written by Isaac Davies on 5-5-2023    ###
##   for any issues email isaac.davies@nike.com    ##
### God cannot be found here, only StackExchange  ###
#####################################################
import pandas as pd
import glob
import numpy as np
import scipy
import math
import re

class processFolder:

    def cleanup(self,f):
        print(f)
        # read in raw data
        df = pd.read_csv(f)
        # filter for only force and displacement
        data = [col for col in df.columns if 'Force' in col or 'Load' in col or 'Displacement' in col]
        df2 = df[data]
        df2.columns = ['Force (N)','Displacement (mm)']
        df2= df2*-1
        #find index location of all peaks
        peaks = scipy.signal.find_peaks(df2['Force (N)'],height=400,distance=100)

        # find index of all midpoints between peak locations
        valley = [0]
        for x in np.arange(len(peaks[0])):
            if x+1==len(peaks[0]):
                continue
            else:
                valley.append(math.ceil(peaks[0][x]+(peaks[0][x+1]-peaks[0][x])/2))
        valley.append(df2.index.tolist()[-1])
        
        # create a list of the indexs for peaks and mid points
        # these will be used to determine the start of a sinlge run, its peak force/displacement, and the end of a run
        pntsOI = list(peaks[0])
        for x in valley:
            pntsOI.append(x)
        pntsOI.sort()
        
        
        #find the points at which we switch the target force
        break500 = pntsOI[pntsOI.index(peaks[0][49])+1]
        try:
            break1000 = pntsOI[pntsOI.index(peaks[0][99])+1]
        except:
            break1000 = pntsOI[pntsOI.index(peaks[0][-1])]
        try:
            break1500 = pntsOI[pntsOI.index(peaks[0][149])+1]
        except Exception as e:
            print(e)
        
        df2.loc[:break500,'Target'] = 500
        try:
            df2.loc[break500+1:break1000,'Target'] = 1000
            try:
                df2.loc[break1000+1:break1500,'Target'] = 1500
                df2.loc[break1500+1:,'Target'] = 2000
            except Exception as e:
                try:
                    df2.loc[break1000+1:,'Target'] = 1500
                except Exception as e:
                    print(e)
        except:
            df2.loc[break500+1:,'Target'] = 1000

        self.rawData = df2
        self.peaks = peaks[0]
        self.pntsOI = pntsOI
#----------------------------------------------------------------------------------
#----------------------------------------------------------------------------------
#----------------------------------------------------------------------------------
#----------------------------------------------------------------------------------
    def cycleFind(self):
        #create output dataframe
        cols= ['start','peak','end','cycleNum','target']
        self.cyc = pd.DataFrame(columns=cols)
        
        #cycle through each target force
        for target, df in self.rawData.loc[self.peaks].groupby('Target'):
            # do a 5 point rolling average
            stdev = df.rolling(5,center=True).std()
            # find rolling average with the lowest standard deviation
            minIndex = stdev.loc[stdev['Force (N)'] == stdev['Force (N)'].min()].index.to_list()[0]

            # construct the indecies for the start, peak, and end of the cycle
            start = self.pntsOI[self.pntsOI.index(minIndex)-1]
            end = self.pntsOI[self.pntsOI.index(minIndex)+1]

            #find the cycle number
            cycle = np.where(self.peaks==minIndex)[0][0]
            
            # add the slice of the frame to the output and include the cycle number
            df2 = pd.DataFrame([[start,minIndex,end,cycle,target]],columns=cols)
            self.cyc = pd.concat([self.cyc,df2])

#----------------------------------------------------------------------------------
#----------------------------------------------------------------------------------
#----------------------------------------------------------------------------------
#----------------------------------------------------------------------------------

    def calc(self,f):
        cols = ['TR Sample Name','Target','Cycle',
                    'Max Load','Max Deflection',
                    'Energy In', 'Energy Return',
                    'Energy Efficiency','Avg Stiffness']
        self.summary = pd.DataFrame(columns=cols)
        
        self.fdCurve = pd.DataFrame(columns=['Force (N)','Displacement (mm)','Target','Phase',
                                        'Z-height (mm)','% Displacement']) # the full FvsD curve 
        
        
        temp = re.findall(r'[^\\]+(?=\.)',f)
        TRname = re.split('\.',temp[0])[0]
        self.sampleName = self.params.loc[self.params['TR Sample Name']==TRname]['Sample Name'].values[0]
        arr = re.split('-',TRname)
        hl = 'heel'
        ff = 'forefoot'
        loc= None
        if hl.lower() in (item.lower() for item in temp[0]):
            loc = 'HEEL'
            print('heel')
        elif ff.lower() in (item.lower() for item in temp[0]):
            loc = 'FOREFOOT'
        else:
            print("NOT LOCATION FOUND")
        
        if loc == 'HEEL':
            height = self.params.loc[self.params['TR Sample Name']==TRname]['Heel height'].values[0]
        elif loc == 'FOREFOOT':
            height = self.params.loc[self.params['TR Sample Name']==TRname]['FF height'].values[0]
        else:
            height = None
        
        
        # do each calulation for each target load
        for target, df in self.rawData.groupby('Target'):
            print(target)

            frame = self.cyc.loc[self.cyc.target==target]
            try:
                cycle = frame.cycleNum.values[0]
            except:
                continue

            # break data into compression and release views
            compress = df.loc[frame.start.values[0]:frame.peak.values[0]]
            release = df.loc[frame.peak.values[0]:frame.end.values[0]]
            compress['Phase'] = 'Loading'
            release['Phase'] = 'Unloading'

            # get the x and y values specifically for the Avg stiffness
            xStiff = compress.loc[compress['Force (N)']>100]['Displacement (mm)']
            yStiff = compress.loc[compress['Force (N)']>100]['Force (N)']

            # get x and y values for full compression and release
            xin = compress['Displacement (mm)']
            yin = compress['Force (N)']
            xout = release['Displacement (mm)']
            yout = release['Force (N)']

            # do all the calculations for the output
            stiffness = np.polyfit(xStiff,yStiff,1)[0] #linear fit for stiffness
            Ein = np.trapz(y=yin,x=xin)/1000    #energy in compression (J)
            Eout = np.trapz(y=yout,x=xout)/-1000 #energy returned in release (J)
            eff = Eout/Ein*100
            max_d = xin.max()
            max_f = yin.max()
            
            self.fdCurve = pd.concat([self.fdCurve,compress,release])
            self.fdCurve['Z-height (mm)'] = height
            self.fdCurve['% Displacement'] = self.fdCurve['Displacement (mm)']/self.fdCurve['Z-height (mm)']
            self.fdCurve['Location'] = loc
            df2 = pd.DataFrame([[TRname,target,cycle,max_f,max_d,Ein,Eout,eff,stiffness]],columns=cols)
            self.summary = pd.concat([self.summary,df2])

#----------------------------------------------------------------------------------
#----------------------------------------------------------------------------------
#----------------------------------------------------------------------------------
#----------------------------------------------------------------------------------
  
            

    def __init__(self,folder,savename,params):
        self.folder = folder            # this is the **tracking.csv file full name
        self.params = pd.read_csv(f'{folder}/Parameters.csv')            # this will be a DataFrame with TR Name|Form|Oven|PSI|Size|L\R|Tup|Heel height|FF height
        self.files = glob.glob(fr'{folder}/**/*tracking.csv',recursive=True)

        cols = ['TR Sample Name','Target','Cycle',
            'Max Load','Max Deflection',
            'Energy In', 'Energy Return',
            'Energy Efficiency','Avg Stiffness']

        self.results = pd.DataFrame(columns = cols)
        self.singleCurve = pd.DataFrame()

        self.params = params

        for f in self.files:
            self.cleanup(f)
            self.cycleFind()
            self.calc(f)
            self.fdCurve['Sample Name'] = self.sampleName
            self.results= pd.concat([self.results,self.summary])
            self.singleCurve = pd.concat([self.singleCurve,self.fdCurve])
        
        self.final = self.results.merge(self.params,how='left', left_on='TR Sample Name', right_on='TR Sample Name')

        cols = ['TR Number','TR Sample Name','Form', 'Leave this Blank','Sample Name',
        'PSI', 'Size', 'Left/Right', 'Tup','Location',
        'Target', 'Cycle', 'Max Load', 'Max Deflection',
        'Energy In', 'Energy Return', 'Energy Efficiency', 'Avg Stiffness', 
        'Heel height', 'FF height']

        self.final = self.final[cols]

        colUser = ['TR Number','TR Sample Name','Form','Oven Treatment (°C/min)','Sample Name',
                   'PSI','Size','Left/Right','Tup','Location',
                   'Target (N)','Cycle','Max Load (N)','Max Deflection (mm)',
                   'Energy In (J)','Energy Out (J)','Energy Efficiency (%)','Avg Stiffness (N/mm)',
                   'Heel Height (mm)','FF Height (mm)']
        naming = dict(zip(cols, colUser))
        self.final.rename(columns=naming,inplace=True)

        self.singleCurve.to_csv(fr'{folder}\{savename} Single Curve Hysteresis.csv',index=False)
        self.final.to_csv(fr'{folder}\{savename} summary.csv',index=False)
        print("\n#############################\nProcessing complete!\n#############################")

        

