{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "import pandas as pd"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 1,
   "metadata": {},
   "outputs": [
    {
     "ename": "SyntaxError",
     "evalue": "unexpected EOF while parsing (<ipython-input-1-77cf91b35c56>, line 2)",
     "output_type": "error",
     "traceback": [
      "\u001b[1;36m  File \u001b[1;32m\"<ipython-input-1-77cf91b35c56>\"\u001b[1;36m, line \u001b[1;32m2\u001b[0m\n\u001b[1;33m    \u001b[0m\n\u001b[1;37m    ^\u001b[0m\n\u001b[1;31mSyntaxError\u001b[0m\u001b[1;31m:\u001b[0m unexpected EOF while parsing\n"
     ]
    }
   ],
   "source": [
    "def calculate_freq_timeouts(df, cols_groupby):\n",
    "    \n",
    "# Collecting the number of trials in each groupby group - now dividing also by rat\n",
    "total = latencies.groupby(cols_groupby)['cp_lat' ].count()\n",
    "\n",
    "# Collecting the number of trials with latency to cp between 10 and 30 s (timeouts)\n",
    "timeout_mask = latencies['cp_lat'].between(10, 30)\n",
    "timeout_runs = latencies[timeout_mask]\n",
    "timeouts = timeout_runs.groupby(cols_groupby)['cp_lat'].count()\n",
    "\n",
    "# Calculate the proportion of timeouts per group\n",
    "freq_timeouts = timeouts/total\n",
    "freq_timeouts = freq_timeouts.reset_index()\n",
    "\n",
    "return freq_timeouts\n",
    "    "
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.6.4"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}
