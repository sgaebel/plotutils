import autocorr as ac
import bz2
import emcee
import numpy as np
import os
import os.path as op

class EnsembleSamplerRunner(object):
    """Runner object for an emcee sampler.

    """

    def __init__(self, sampler, pts):
        """Initialise the runner with the given sampler and initial ensemble
        position.

        """

        self.sampler = sampler
        self.result = pts
        self._first_step = True

        self.thin = 1

    @property
    def chain(self):
        """The current state of the sampler's chain.

        """
        return self.sampler.chain

    @property
    def lnprobability(self):
        """The current state of the sampler's lnprobability.

        """
        return self.sampler.lnprobability

    @property
    def thin_chain(self):
        """Return a thinned chain (if possible), using
        :func:`ac.emcee_thinned_chain`

        """
        return ac.emcee_thinned_chain(self.chain)

    @property
    def acls(self):
        """Return the estimate of the current chain's autocorrelation lengths,
        using :func:`plotutils.autocorr.emcee_chain_autocorrelation_lengths`.

        """
        return ac.emcee_chain_autocorrelation_lengths(self.chain)

    def save_state(self, dir):
        """Save the state of the runner stored chain, lnprob, and thin
        parameter in the given directory.  Three files will be created
        (approximately atomically, so the operation is nearly safe
        from interruption):

         * ``chain.npy.bz2``
         * ``lnprob.npy.bz2``
         * ``thin.txt``

        Storing the current chain, lnprob and the thin parameter.

        """

        with bz2.BZ2File(op.join(dir, 'chain.npy.bz2.temp'), 'w') as out:
            np.save(out, self.chain)
        with bz2.BZ2File(op.join(dir, 'lnprob.npy.bz2.temp'), 'w') as out:
            np.save(out, self.lnprobability)
        with open(op.join(dir, 'thin.txt.temp'), 'w') as out:
            out.write('{0:d}\n'.format(self.thin))

        try:
            os.rename(op.join(dir, 'chain.npy.bz2.temp'),
                      op.join(dir, 'chain.npy.bz2'))
            os.rename(op.join(dir, 'lnprob.npy.bz2.temp'),
                      op.join(dir, 'lnprob.npy.bz2'))
            os.rename(op.join(dir, 'thin.txt.temp'),
                      op.join(dir, 'thin.txt'))
        except:
            print 'WARNING: EnsembleSamplerRunner: interrupted during save, inconsistent saved state'
            raise

    def load_state(self, dir):
        """Load a stored state from the given directory.

        """
        try:
            with bz2.BZ2File(op.join(dir, 'chain.npy.bz2'), 'r') as inp:
                self.sampler._chain = np.load(inp)
            with bz2.BZ2File(op.join(dir, 'lnprob.npy.bz2'), 'r') as inp:
                self.sampler._lnprob = np.load(inp)
            with open(op.join(dir, 'thin.txt'), 'r') as inp:
                self.thin = int(inp.readline())

            self.result = self.chain[:,-1,:]
            self._first_step = True
        except:
            print 'WARNING: EnsembleSamplerRunner: interrupted during load, inconsistent loaded state'
            raise

    def run_mcmc(self, nthinsteps):
        """Run the associated sampler to produce ``nthinsteps`` worth of
        stored ensembles (i.e. the sampler will be run for
        ``nthinsteps*self.thin`` total steps).

        """

        nsteps = self.thin * nthinsteps
        
        if self._first_step:
            self.result = self.sampler.run_mcmc(self.result, nsteps, thin=self.thin)
            self._first_step = False
        else:
            self.result = self.sampler.run_mcmc(self.result[0], nsteps, lnprob0=self.result[1], thin=self.thin)

        return self.result

    def rethin(self):
        """Increase the thinning parameter by a factor of two, modifying the
        stored chain and lnprob states accordingly.  

        """

        self.sampler._chain = self.sampler._chain[:,1::2,:]
        self.sampler._lnprob = self.sampler._lnprob[:,1::2]
        self.thin *= 2
