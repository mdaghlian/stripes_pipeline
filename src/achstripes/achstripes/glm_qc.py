"""
glm_qc.py
=========
Interactive, self-contained HTML QC reports for a single GLMsingle run
(one task/sequence), in the same lightweight-Plotly, no-server style as
``cvl_utils.qc_plots`` (hypot_code). Meant to be dropped in right after
``GLM_single.fit(...)`` to sanity-check, in one page: the assumed/fit HRF,
the GLMdenoise noise pool and how many noise regressors it picked,
cross-validated R2 (overall and per run), and any contrast maps you've
already computed downstream (e.g. colour - bw).

Only needs numpy + plotly (both already pulled in transitively via
cvl_utils/pycortex in the stripes conda env).

GLMsingle output field reference, for context (from cvnlab/GLMsingle,
``glmsingle.py`` -- field names/shapes below were read directly from that
source, not guessed):

    results['typea']  -> onoffR2, meanvol, betasmd
    results['typeb']  -> FitHRFR2, FitHRFR2run, HRFindex, HRFindexrun,
                          R2, R2run, betasmd, meanvol
    results['typec']  -> HRFindex, HRFindexrun, glmbadness, pcvoxels,
                          pcnum, xvaltrend, noisepool, pcregressors,
                          betasmd, R2, R2run, meanvol
    results['typed']  -> as typec, plus rrbadness, FRACvalue, scaleoffset
    results['designinfo'] -> design, stimdur, tr, params (incl.
                          hrflibrary, hrftoassume), designSINGLE,
                          stimorder, numtrialrun, condcounts, condinruns,
                          endbuffers
    results['runwisefir']  -> firR2, firtcs, firavg, firgrandavg

R2 / R2run / onoffR2 / FitHRFR2 are percentages (0-100), not fractions.
betasmd is in percent-BOLD-change units by default (GLMsingle's
``wantpercentbold=1`` default), *unless* that was overridden when
``.fit()`` was called.

Every report-building function below takes plain dicts/arrays -- pass
whichever of ``results['typec']`` / ``results['typeb']`` /
``results['runwisefir']`` / ``results['designinfo']`` you have (e.g. only
``typeb`` if you ran with ``wantglmdenoise=0``); missing pieces just make
their section note itself as skipped rather than raising.

Typical usage, right after fitting::

    from achstripes.glm_qc import build_glmsingle_qc_report

    results[key] = glms[key].fit(design, data, stimdur, tr, outputdir=tglm_path)

    build_glmsingle_qc_report(
        opj(qc_dir, f'{key}_qc.html'),
        subject=subject, label=key,
        typec=results[key]['typec'],
        runwisefir=results[key]['runwisefir'],
        designinfo=results[key]['designinfo'],
        contrasts={'colour-bw': betas_full['col'] - betas_full['bw']},
    )

Each individual ``*_plot`` function also returns a plain ``plotly.graph_objects.Figure``
you can call ``.show()`` / ``.write_html()`` on by itself in a notebook, if
you just want one panel rather than the full report.
"""

import os, glob
opj = os.path.join
import numpy as np
import nibabel as nib
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

try:
    from plotly.offline import get_plotlyjs as _get_plotlyjs
except ImportError:  # pragma: no cover - very old plotly
    _get_plotlyjs = None


# --------------------------------------------------------------------- #
# low-level: scrollable 3-plane volume viewer (own slider per plane, no
# click-crosshair -- kept deliberately simple so many of these can be
# embedded on one report page without JS/id collisions; for a full
# click-crosshair single-volume viewer see cvl_utils.qc_plots.ortho_view_plot)
# --------------------------------------------------------------------- #

def _ortho_slider(
    vol,
    vmin: float = None,
    vmax: float = None,
    colorscale: str = 'gray',
    pct_clip: float = 99.5,
    symmetric: bool = False,
    title: str = None,
    height: int = 340,
    width: int = 1000,
):
    """
    Sagittal/coronal/axial viewer for one 3D volume, each panel with its
    own independent slice slider.

    Parameters
    ----------
    vol : (X, Y, Z) array
    vmin, vmax : float, optional
        Color range. If not given: ``[0, pct_clip percentile]`` normally,
        or ``[-m, m]`` (m = pct_clip percentile of |vol|) if *symmetric*.
    symmetric : bool
        Use a signed, zero-centered color range -- for contrast/difference
        maps that can be negative (pairs well with a diverging
        *colorscale* like ``'RdBu_r'``).
    """
    vol = np.asarray(vol)
    if vol.ndim != 3:
        raise ValueError('_ortho_slider: expected a 3D (X, Y, Z) array, got shape {}'.format(vol.shape))

    nx, ny, nz = vol.shape
    finite = vol[np.isfinite(vol)]
    if symmetric:
        m = float(np.percentile(np.abs(finite), pct_clip)) if finite.size else 1.0
        m = m or 1.0
        if vmin is None:
            vmin = -m
        if vmax is None:
            vmax = m
    else:
        if vmin is None:
            vmin = 0.0
        if vmax is None:
            vmax = float(np.percentile(finite, pct_clip)) if finite.size else 1.0
            vmax = vmax or 1.0

    i0, j0, k0 = nx // 2, ny // 2, nz // 2
    common = dict(zmin=vmin, zmax=vmax, colorscale=colorscale, showscale=True)

    def sag(i): return np.rot90(vol[i, :, :])
    def cor(j): return np.rot90(vol[:, j, :])
    def ax(k): return np.rot90(vol[:, :, k])

    frames = (
        [go.Frame(name='sag-{}'.format(i), traces=[0], data=[go.Heatmap(z=sag(i), **common)]) for i in range(nx)]
        + [go.Frame(name='cor-{}'.format(j), traces=[1], data=[go.Heatmap(z=cor(j), **common)]) for j in range(ny)]
        + [go.Frame(name='ax-{}'.format(k), traces=[2], data=[go.Heatmap(z=ax(k), **common)]) for k in range(nz)]
    )

    fig = make_subplots(rows=1, cols=3, subplot_titles=('sagittal', 'coronal', 'axial'))
    fig.add_trace(go.Heatmap(z=sag(i0), **common), row=1, col=1)
    fig.add_trace(go.Heatmap(z=cor(j0), **common), row=1, col=2)
    fig.add_trace(go.Heatmap(z=ax(k0), **common), row=1, col=3)
    fig.frames = frames

    def _slider(axis_label, n, active, x0, prefix):
        return dict(
            active=active, x=x0, len=0.30, xanchor='left', y=-0.10,
            currentvalue=dict(prefix=prefix, font=dict(size=11)),
            pad=dict(t=10),
            steps=[
                dict(method='animate', label=str(v),
                     args=[['{}-{}'.format(axis_label, v)],
                           dict(mode='immediate', frame=dict(duration=0, redraw=True))])
                for v in range(n)
            ],
        )

    fig.update_layout(
        title=title or 'volume viewer',
        height=height,
        width=width,
        margin=dict(t=60, b=100, l=20, r=20),
        sliders=[
            _slider('sag', nx, i0, 0.0, 'x: '),
            _slider('cor', ny, j0, 0.36, 'y: '),
            _slider('ax', nz, k0, 0.72, 'z: '),
        ],
    )
    for ax_name in ('xaxis', 'xaxis2', 'xaxis3'):
        fig.update_layout({ax_name: dict(visible=False)})
    for ax_name in ('yaxis', 'yaxis2', 'yaxis3'):
        fig.update_layout({ax_name: dict(visible=False, scaleanchor=ax_name.replace('yaxis', 'x'))})
    return fig


# --------------------------------------------------------------------- #
# volume-level panels
# --------------------------------------------------------------------- #

def meanvol_plot(meanvol, title: str = None):
    """`results['typec']['meanvol']` (or typea/typeb) -- mean functional volume."""
    return _ortho_slider(meanvol, colorscale='gray', title=title or 'mean functional volume')


def r2_map_plot(R2, title: str = None):
    """
    Cross-validated model R2 map (`results['typec']['R2']` /
    `['typeb']['R2']`), in percent (GLMsingle convention, not 0-1).
    """
    return _ortho_slider(R2, vmin=0, vmax=100, colorscale='hot',
                          title=title or 'model R² (cross-validated, %)')


def hrf_index_map_plot(HRFindex, title: str = None):
    """
    Per-voxel index into the HRF library (`results[...]['HRFindex']`).
    If you ran with `wantlibrary=0` (single assumed HRF for every voxel,
    as in the stripes pipeline default), this map is *expected* to be
    uniform -- that's noted in the title rather than left looking broken.
    """
    HRFindex = np.asarray(HRFindex, dtype=float)
    finite = HRFindex[np.isfinite(HRFindex)]
    uniform = finite.size and (np.nanmin(finite) == np.nanmax(finite))
    note = ' -- uniform (wantlibrary=0: single assumed HRF for every voxel)' if uniform else ''
    vmax = float(np.nanmax(finite)) if finite.size else 1.0
    return _ortho_slider(HRFindex, vmin=0, vmax=max(vmax, 1.0), colorscale='turbo',
                          title=(title or 'HRF index') + note)


def noise_pool_plot(noisepool, title: str = None):
    """
    GLMdenoise noise-pool mask (`results['typec']['noisepool']`) -- the
    (bright, task-poor-R2) voxels used to derive the candidate noise
    regressors. The flagged fraction is of the *whole array* (not a brain
    mask, since GLMsingle's own brain threshold isn't returned separately)
    so treat the percentage as a rough sanity check, not a precise stat.
    """
    noisepool = np.asarray(noisepool)
    frac = 100.0 * np.count_nonzero(noisepool) / noisepool.size if noisepool.size else 0.0
    return _ortho_slider(noisepool.astype(float), vmin=0, vmax=1, colorscale='gray',
                          title=(title or 'GLMdenoise noise pool') + ' -- {:.1f}% of array voxels flagged'.format(frac))


def contrast_map_plot(contrast_vol, name: str = 'contrast', pct_clip: float = 99.5, title: str = None):
    """
    A signed contrast/effect-size volume you've already computed downstream
    (e.g. `betas_full['col'] - betas_full['bw']`) -- diverging colorscale,
    symmetric range from the *pct_clip* percentile of |values|.
    """
    return _ortho_slider(np.asarray(contrast_vol), symmetric=True, colorscale='RdBu_r',
                          pct_clip=pct_clip, title=title or name)


# --------------------------------------------------------------------- #
# timeseries / curve panels
# --------------------------------------------------------------------- #

def hrf_fir_plot(runwisefir, tr: float = None, hrf_library=None, hrf_assumed=None, title: str = None):
    """
    HRF shape sanity check, from GLMsingle's own diagnostic run-wise FIR
    fit (`results['runwisefir']`, computed internally regardless of
    `wantlibrary`).

    Left panel: `firavg` (one curve per run) + `firgrandavg` (bold) -- the
    FIR-estimated response to an average trial, i.e. what the data itself
    says the response looks like, independent of whatever HRF you assumed.
    Compare its peak time/shape against the assumed HRF on the right to
    judge whether the canonical-HRF assumption is reasonable for this scan.

    Right panel (only drawn if *hrf_library* and/or *hrf_assumed* are
    given -- e.g. from `results['designinfo']['params']['hrflibrary']` /
    `['hrftoassume']`): the HRF(s) actually available/used.
    """
    firavg = np.asarray(runwisefir['firavg'])
    firgrandavg = np.asarray(runwisefir['firgrandavg'])
    nruns, ntime = firavg.shape
    t = np.arange(ntime) * tr if tr else np.arange(ntime)

    show_hrf_panel = hrf_library is not None or hrf_assumed is not None
    ncols = 2 if show_hrf_panel else 1
    titles = ('run-wise FIR response (diagnostic)', 'HRF library / assumed')[:ncols]
    fig = make_subplots(rows=1, cols=ncols, subplot_titles=titles)

    for r in range(nruns):
        fig.add_trace(go.Scatter(x=t, y=firavg[r], mode='lines', name='run {}'.format(r + 1),
                                  line=dict(width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=t, y=firgrandavg, mode='lines', name='run avg',
                              line=dict(color='black', width=3)), row=1, col=1)

    if show_hrf_panel:
        if hrf_library is not None:
            hrf_library = np.atleast_2d(np.asarray(hrf_library))
            if hrf_library.shape[0] == 1:
                hrf_library = hrf_library.T
            xlib = np.arange(hrf_library.shape[0]) * tr if tr else np.arange(hrf_library.shape[0])
            for h in range(hrf_library.shape[1]):
                fig.add_trace(go.Scatter(x=xlib, y=hrf_library[:, h], mode='lines',
                                          name='library HRF {}'.format(h + 1),
                                          line=dict(width=1, dash='dot')), row=1, col=2)
        if hrf_assumed is not None:
            hrf_assumed = np.asarray(hrf_assumed).ravel()
            xas = np.arange(len(hrf_assumed)) * tr if tr else np.arange(len(hrf_assumed))
            fig.add_trace(go.Scatter(x=xas, y=hrf_assumed, mode='lines', name='assumed HRF',
                                      line=dict(color='black', width=3)), row=1, col=2)

    xlabel = 'time from trial onset (s)' if tr else 'TR from trial onset'
    fig.update_xaxes(title_text=xlabel)
    fig.update_yaxes(title_text='BOLD (%)', row=1, col=1)
    fig.update_layout(title=title or 'HRF check', height=420, width=520 * ncols + 100,
                       margin=dict(t=60, b=50, l=60, r=20))
    return fig


def xvaltrend_plot(xvaltrend, pcnum: int, title: str = None):
    """
    GLMdenoise's noise-regressor-count selection curve
    (`results['typec']['xvaltrend']` / `['pcnum']`) -- mirrors GLMsingle's
    own diagnostic figure (cross-validated held-out accuracy vs. number of
    candidate noise PCs included), just interactive. The starred point is
    the number of PCs GLMsingle actually selected for the final model. A
    curve that's still climbing steeply at the selected point (rather than
    plateauing) is worth a second look -- it can mean the selection was cut
    off early, or that the noise pool isn't well separated from signal.
    """
    xvaltrend = np.asarray(xvaltrend).ravel()
    n = len(xvaltrend)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(range(n)), y=xvaltrend, mode='lines+markers', name='xvaltrend'))
    if 0 <= pcnum < n:
        fig.add_trace(go.Scatter(x=[pcnum], y=[xvaltrend[pcnum]], mode='markers',
                                  marker=dict(color='red', size=14, symbol='star'),
                                  name='selected (pcnum={})'.format(pcnum)))
    fig.update_layout(
        title=title or 'GLMdenoise: noise-regressor count selection',
        xaxis_title='number of GLMdenoise PCs included',
        yaxis_title='cross-validated accuracy (−median held-out error; higher = better)',
        height=380, width=650, margin=dict(t=60, b=50, l=60, r=20),
    )
    return fig


def noise_regressor_plot(pcregressors, pcnum: int = None, tr: float = None, title: str = None):
    """
    The GLMdenoise candidate noise-regressor timeseries, per run
    (`results['typec']['pcregressors']`, a list of (time x n_pcs+1)
    arrays). If *pcnum* is given (`results['typec']['pcnum']`), only the
    first *pcnum* columns -- the ones actually used in the final model --
    are drawn.
    """
    nruns = len(pcregressors)
    fig = make_subplots(rows=nruns, cols=1, shared_xaxes=True,
                         subplot_titles=['run {}'.format(r + 1) for r in range(nruns)])
    total_available = 0
    for r, reg in enumerate(pcregressors):
        reg = np.asarray(reg)
        total_available = max(total_available, reg.shape[1])
        ncols = reg.shape[1] if pcnum is None else min(pcnum, reg.shape[1])
        x = np.arange(reg.shape[0]) * tr if tr else np.arange(reg.shape[0])
        for c in range(ncols):
            fig.add_trace(
                go.Scatter(x=x, y=reg[:, c], mode='lines', name='pc {}'.format(c + 1),
                           legendgroup='pc{}'.format(c + 1), showlegend=(r == 0)),
                row=r + 1, col=1,
            )
    suffix = ''
    if pcnum is not None:
        suffix = ' (first {} of {} shown -- the number actually used)'.format(pcnum, total_available)
    fig.update_layout(title=(title or 'GLMdenoise noise regressors') + suffix,
                       height=170 * nruns + 90, width=950, margin=dict(t=60, b=50, l=60, r=20))
    fig.update_xaxes(title_text='time (s)' if tr else 'TR', row=nruns, col=1)
    return fig


def r2_by_run_plot(R2run, title: str = None):
    """
    Mean cross-validated R2 per run (`results[...]['R2run']`, X x Y x Z x
    nruns) -- a quick way to spot one bad/noisy run without scrolling
    through the full volume slice by slice. Averaged only over voxels with
    R2 > 0 (i.e. voxels the model considers better than a null/mean
    predictor), so the handful of large-negative-R2 outlier voxels typical
    at brain edges/CSF don't dominate the summary.
    """
    R2run = np.asarray(R2run)
    nruns = R2run.shape[-1]
    means = []
    for r in range(nruns):
        vol = R2run[..., r]
        pos = vol[vol > 0]
        means.append(float(np.mean(pos)) if pos.size else float('nan'))
    fig = go.Figure(go.Bar(x=['run {}'.format(r + 1) for r in range(nruns)], y=means))
    fig.update_layout(title=title or 'mean R² per run (voxels with R² > 0)',
                       yaxis_title='mean R² (%)', height=350, width=max(120 * nruns + 200, 400),
                       margin=dict(t=60, b=50, l=60, r=20))
    return fig


# --------------------------------------------------------------------- #
# report assembly
# --------------------------------------------------------------------- #

def _fig_div(fig):
    return pio.to_html(fig, include_plotlyjs=False, full_html=False)


_PAGE_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
 body {{ font-family: -apple-system, Helvetica, Arial, sans-serif; margin: 24px; color: #222; }}
 h1 {{ margin-bottom: 4px; }}
 .subtitle {{ color: #666; margin-top: 0; margin-bottom: 28px; }}
 h2 {{ border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-top: 44px; }}
 .section-note {{ color: #888; font-style: italic; font-size: 0.92em; margin-top: -6px; margin-bottom: 14px; }}
 .fig-row {{ display: flex; flex-wrap: wrap; gap: 12px; }}
</style>
{plotly_js}
</head>
<body>
<h1>{title}</h1>
<p class="subtitle">{subtitle}</p>
{body}
</body>
</html>
"""


def build_glmsingle_qc_report(
    out_html: str,
    subject: str = None,
    label: str = None,
    typec: dict = None,
    typeb: dict = None,
    runwisefir: dict = None,
    designinfo: dict = None,
    contrasts: dict = None,
    tr: float = None,
):
    """
    Assemble one self-contained HTML QC report for a single GLMsingle run
    (one task/sequence): HRF check, GLMdenoise noise pool + regressor
    selection, cross-validated R2, and any contrast maps you've already
    computed. Meant to be called right after `GLM_single.fit(...)`::

        results[key] = glms[key].fit(design, data, stimdur, tr, outputdir=tglm_path)
        build_glmsingle_qc_report(
            opj(qc_dir, f'{key}_qc.html'),
            subject=subject, label=key,
            typec=results[key]['typec'],
            runwisefir=results[key]['runwisefir'],
            designinfo=results[key]['designinfo'],
            contrasts={'colour-bw': betas_full['col'] - betas_full['bw']},
        )

    Every dict argument is optional -- pass whatever you actually have
    (e.g. `typeb=` instead of `typec=` if you ran with
    `wantglmdenoise=0`; leave out `contrasts` before you've computed one).
    Sections with nothing to show are noted as skipped rather than
    raising, so this is safe to call at any point in the analysis, not
    just at the very end.

    Parameters
    ----------
    out_html : str
        Path to write the report to (parent dir created if needed).
    subject, label : str, optional
        Shown in the report header, e.g. `label='bwcol-1mmTR3000'`.
    typec, typeb : dict, optional
        `results['typec']` / `results['typeb']` -- whichever model type
        you kept. `typec` (needs `wantglmdenoise=1`) is required for the
        noise-pool/xvaltrend/noise-regressor panels; either unlocks the
        R2 and HRF-index panels.
    runwisefir : dict, optional
        `results['runwisefir']` -- powers the HRF-shape-check panel.
    designinfo : dict, optional
        `results['designinfo']` -- supplies `tr` (if not passed
        explicitly) and the HRF library/assumed-HRF curves.
    contrasts : dict[str, ndarray], optional
        Named contrast volumes you've already computed downstream, each
        rendered as its own scrollable signed (RdBu) volume panel.
    tr : float, optional
        Overrides `designinfo['tr']` for the x-axis units on timeseries
        panels; falls back to TR-index units if neither is available.

    Returns
    -------
    out_html : str
    """
    model = typec or typeb
    if model is None and runwisefir is None and not contrasts:
        raise ValueError(
            'build_glmsingle_qc_report: nothing to report -- pass at least one of '
            'typec/typeb, runwisefir, or contrasts')

    if tr is None and designinfo is not None:
        tr = designinfo.get('tr')

    sections = []  # list of (heading, note_or_None, [div_html, ...])

    # --- HRF ---
    hrf_divs = []
    if runwisefir is not None:
        hrf_lib = hrf_assumed = None
        if designinfo is not None:
            p = designinfo.get('params', {}) or {}
            hrf_lib = p.get('hrflibrary')
            hrf_assumed = p.get('hrftoassume')
        hrf_divs.append(_fig_div(hrf_fir_plot(runwisefir, tr=tr, hrf_library=hrf_lib, hrf_assumed=hrf_assumed)))
    if model is not None and model.get('HRFindex') is not None:
        hrf_divs.append(_fig_div(hrf_index_map_plot(model['HRFindex'])))
    sections.append((
        'HRF',
        None if hrf_divs else 'skipped -- pass runwisefir and/or typec/typeb',
        hrf_divs,
    ))

    # --- GLMdenoise / noise pool ---
    gd_divs = []
    if typec is not None and typec.get('noisepool') is not None:
        gd_divs.append(_fig_div(noise_pool_plot(typec['noisepool'])))
        if typec.get('xvaltrend') is not None and typec.get('pcnum') is not None:
            gd_divs.append(_fig_div(xvaltrend_plot(typec['xvaltrend'], typec['pcnum'])))
        if typec.get('pcregressors') is not None:
            gd_divs.append(_fig_div(noise_regressor_plot(typec['pcregressors'], pcnum=typec.get('pcnum'), tr=tr)))
    sections.append((
        'GLMdenoise / noise pool',
        None if gd_divs else 'skipped -- pass typec (needs wantglmdenoise=1); this section is typec-only',
        gd_divs,
    ))

    # --- model fit (R2) ---
    r2_divs = []
    if model is not None and model.get('R2') is not None:
        r2_divs.append(_fig_div(r2_map_plot(model['R2'])))
        if model.get('R2run') is not None:
            r2_divs.append(_fig_div(r2_by_run_plot(model['R2run'])))
    sections.append((
        'Model fit (R²)',
        None if r2_divs else 'skipped -- pass typec or typeb',
        r2_divs,
    ))

    # --- contrasts ---
    c_divs = []
    if contrasts:
        for name, vol in contrasts.items():
            c_divs.append(_fig_div(contrast_map_plot(np.asarray(vol), name=name, title=name)))
    sections.append((
        'Contrasts',
        None if c_divs else 'skipped -- pass contrasts={name: array} for already-computed contrast volumes',
        c_divs,
    ))

    body_parts = []
    for heading, note, divs in sections:
        body_parts.append('<h2>{}</h2>'.format(heading))
        if note:
            body_parts.append('<p class="section-note">{}</p>'.format(note))
        if divs:
            body_parts.append('<div class="fig-row">{}</div>'.format(''.join(divs)))
    body = '\n'.join(body_parts)

    subtitle = ' / '.join(b for b in (subject, label) if b)

    plotly_js = ''
    if _get_plotlyjs is not None:
        # embed the plotly.js bundle once, inline -- keeps the report a single
        # self-contained file with no CDN/network dependency (matches
        # cvl_utils.qc_plots' fig.write_html() behaviour for single-figure QC)
        plotly_js = '<script type="text/javascript">{}</script>'.format(_get_plotlyjs())
    else:  # pragma: no cover
        plotly_js = '<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>'

    html = _PAGE_TEMPLATE.format(
        title='GLMsingle QC' + (' — {}'.format(label) if label else ''),
        subtitle=subtitle,
        plotly_js=plotly_js,
        body=body,
    )
    os.makedirs(os.path.dirname(out_html) or '.', exist_ok=True)
    with open(out_html, 'w') as f:
        f.write(html)
    return out_html


_NPY_FILES = {
    'typea': 'TYPEA_ONOFF.npy',
    'typeb': 'TYPEB_FITHRF.npy',
    'typec': 'TYPEC_FITHRF_GLMDENOISE.npy',
    'typed': 'TYPED_FITHRF_GLMDENOISE_RR.npy',
    'runwisefir': 'RUNWISEFIR.npy',
}


def _save_nii(arr, affine, out_path, dtype=np.float32):
    img = nib.Nifti1Image(np.asarray(arr).astype(dtype), affine)
    nib.save(img, out_path)
    return out_path


def save_glmsingle_asnii(glm_dir, ref_nii, out_dir=None, include_fir_timecourses=False, overwrite=False):
    """
    Save the spatial (3D/4D) fields from a GLMsingle run's saved `.npy`
    outputs as individual .nii.gz files, so they can be opened directly in
    fsleyes/itksnap/etc for QC rather than only viewed through
    `build_glmsingle_qc_report`'s embedded plots.

    GLMsingle's own arrays carry no spatial affine of their own (their
    official nifti-save example literally uses `np.eye(4)`) -- they're on
    whatever voxel grid the input `data` was on. *ref_nii* should be one of
    the functional runs that actually went into `.fit()` for this
    task/seq, so the affine used here is correct (only the affine is used,
    not the full header, to avoid dtype/scaling mismatches).

    Auto-discovers and loads whichever of the standard GLMsingle output
    files exist in *glm_dir* -- `TYPEA_ONOFF.npy`, `TYPEB_FITHRF.npy`,
    `TYPEC_FITHRF_GLMDENOISE.npy`, `TYPED_FITHRF_GLMDENOISE_RR.npy`,
    `RUNWISEFIR.npy` -- and skips whatever's missing (e.g. no typed file
    if you ran with `wantfracridge=0`, as in the stripes default config).

    Written (file names prefixed by model type, all under
    `glm_dir/qc-nii/` by default)::

        typea_meanvol, typea_onoffR2
        type{b,c,d}_meanvol, _R2, _R2run (4D: x,y,z,run), _HRFindex,
            _betasmd (4D: x,y,z,trial)
        type{c,d}_noisepool, _pcvoxels (binary masks, uint8)
        type{c,d}_glmbadness (4D: x,y,z,1+n_pcs -- reshaped from
            GLMsingle's flattened (voxels, 1+n_pcs); scrub the 4th dim in
            fsleyes to see, voxel by voxel, whether more GLMdenoise PCs
            helped or hurt -- the spatial pattern behind the xvaltrend
            curve in the HTML report)
        typed_FRACvalue, _scaleoffset (4D: x,y,z,2), _rrbadness (4D:
            x,y,z,n_fracs -- same idea as glmbadness, for the ridge
            fraction search)                              [typed only]
        runwisefir_firR2 (4D: x,y,z,run -- transposed from GLMsingle's
            (run,x,y,z)), _firR2_mean (3D: mean across runs)
        runwisefir_firtcs_run{r} (4D: x,y,z,time, one file per run) --
            only written if *include_fir_timecourses* is True: by far the
            largest output (a full per-voxel FIR timecourse per run),
            meant for a deep dive (e.g. checking for depth-dependent HRF
            shape) rather than routine QC.

    Not written (not spatial, or already covered by
    `build_glmsingle_qc_report`'s plots): `pcregressors`, `pcnum`,
    `xvaltrend`, `firavg`, `firgrandavg`, and everything under
    `DESIGNINFO.npy` (design matrices/metadata, not images).

    Parameters
    ----------
    glm_dir : str
        Directory containing the GLMsingle `.npy` outputs for one
        task/seq (i.e. `outputdir=` from `.fit()`).
    ref_nii : str
        Path to a nifti on the same voxel grid as the data given to
        `.fit()` -- its affine is used for every file written here.
    out_dir : str, optional
        Defaults to `glm_dir/qc-nii/`.
    include_fir_timecourses : bool
        Also write the (large) per-run `firtcs` volumes. Default False.
    overwrite : bool
        Re-write files that already exist. Default False (skip existing
        files rather than re-writing them).

    Returns
    -------
    dict[str, str]
        {field_name: path} for every file written (or already present,
        when `overwrite=False` skipped an existing one) this call.
    """
    affine = nib.load(ref_nii).affine
    out_dir = out_dir or opj(glm_dir, 'qc-nii')
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    loaded = {}
    for key, fname in _NPY_FILES.items():
        fpath = opj(glm_dir, fname)
        if os.path.exists(fpath):
            loaded[key] = np.load(fpath, allow_pickle=True).item()

    if not loaded:
        raise ValueError('save_glmsingle_asnii: no GLMsingle .npy outputs found in {}'.format(glm_dir))

    written = {}

    def _write(name, arr, dtype=np.float32):
        out_path = opj(out_dir, name + '.nii.gz')
        if os.path.exists(out_path) and not overwrite:
            written[name] = out_path
            return
        _save_nii(arr, affine, out_path, dtype=dtype)
        written[name] = out_path

    # --- typea ---
    if 'typea' in loaded:
        d = loaded['typea']
        if d.get('meanvol') is not None:
            _write('typea_meanvol', d['meanvol'])
        if d.get('onoffR2') is not None:
            _write('typea_onoffR2', d['onoffR2'])

    # --- typeb / typec / typed: shared fields ---
    for mtype in ('typeb', 'typec', 'typed'):
        if mtype not in loaded:
            continue
        d = loaded[mtype]
        if d.get('meanvol') is not None:
            _write('{}_meanvol'.format(mtype), d['meanvol'])
        if d.get('R2') is not None:
            _write('{}_R2'.format(mtype), d['R2'])
        if d.get('R2run') is not None:
            _write('{}_R2run'.format(mtype), d['R2run'])  # already (x, y, z, nruns)
        if d.get('HRFindex') is not None:
            _write('{}_HRFindex'.format(mtype), d['HRFindex'])
        if d.get('betasmd') is not None:
            _write('{}_betasmd'.format(mtype), d['betasmd'])

    # --- typec / typed only: GLMdenoise diagnostics ---
    for mtype in ('typec', 'typed'):
        if mtype not in loaded:
            continue
        d = loaded[mtype]
        if d.get('noisepool') is not None:
            _write('{}_noisepool'.format(mtype), d['noisepool'], dtype=np.uint8)
        if d.get('pcvoxels') is not None:
            _write('{}_pcvoxels'.format(mtype), d['pcvoxels'], dtype=np.uint8)
        if d.get('glmbadness') is not None and d.get('R2') is not None:
            nx, ny, nz = np.asarray(d['R2']).shape
            glmbadness = np.asarray(d['glmbadness'])
            if glmbadness.shape[0] == nx * ny * nz:
                _write('{}_glmbadness'.format(mtype), glmbadness.reshape(nx, ny, nz, -1))
            else:
                print('save_glmsingle_asnii: {} glmbadness shape {} does not match {} voxels '
                      '-- skipping reshape'.format(mtype, glmbadness.shape, nx * ny * nz))

    # --- typed only: ridge-regularization extras ---
    if 'typed' in loaded:
        d = loaded['typed']
        if d.get('FRACvalue') is not None:
            _write('typed_FRACvalue', d['FRACvalue'])
        if d.get('scaleoffset') is not None:
            _write('typed_scaleoffset', d['scaleoffset'])  # already (x, y, z, 2)
        if d.get('rrbadness') is not None:
            _write('typed_rrbadness', d['rrbadness'])  # already (x, y, z, n_fracs)

    # --- runwisefir ---
    if 'runwisefir' in loaded:
        d = loaded['runwisefir']
        if d.get('firR2') is not None:
            firR2 = np.asarray(d['firR2'])  # (nruns, x, y, z)
            _write('runwisefir_firR2', np.moveaxis(firR2, 0, -1))  # -> (x, y, z, nruns)
            _write('runwisefir_firR2_mean', firR2.mean(axis=0))
        if include_fir_timecourses and d.get('firtcs') is not None:
            firtcs = np.asarray(d['firtcs'])  # (nruns, x, y, z, ntime)
            for r in range(firtcs.shape[0]):
                _write('runwisefir_firtcs_run{}'.format(r + 1), firtcs[r])

    return written

